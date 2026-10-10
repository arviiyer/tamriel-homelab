package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type VM struct {
	ID           int    `json:"id"`
	Node         string `json:"node"`
	TemplateID   int    `json:"template_id"`
	TemplateNode string `json:"template_node"`
	Cores        int    `json:"cores"`
	Memory       int    `json:"memory"`
	Protected    bool   `json:"protected"`
}

type Inventory struct {
	VMs map[string]VM `json:"vms"`
}
type Config struct {
	Directory string   `json:"terraform_dir"`
	Nodes     []string `json:"nodes"`
	Templates map[string]struct {
		ID   int
		Node string
	} `json:"templates"`
	Sizes map[string]struct{ Cores, Memory int } `json:"sizes"`
}
type Change struct {
	Address string `json:"address"`
	Mode    string `json:"mode"`
	Change  struct {
		Actions []string `json:"actions"`
	} `json:"change"`
}

// Reject unrelated drift, replacement, or deletion before applying a saved plan.
func checkPlan(data []byte, name, action string) error {
	var plan struct {
		ResourceChanges []Change `json:"resource_changes"`
		Errored         bool     `json:"errored"`
	}
	if err := json.Unmarshal(data, &plan); err != nil {
		return err
	}
	if plan.Errored {
		return errors.New("Terraform plan contains errors")
	}
	want := map[string]string{"launch": "create", "destroy": "delete", "protect": "update"}[action]
	target := "proxmox_virtual_environment_vm.vm[" + strconv.Quote(name) + "]"
	found := false
	for _, c := range plan.ResourceChanges {
		if strings.Join(c.Change.Actions, ",") == "no-op" {
			continue
		}
		if c.Address != target || c.Mode != "managed" || len(c.Change.Actions) != 1 || c.Change.Actions[0] != want {
			return fmt.Errorf("unexpected plan change at %s", c.Address)
		}
		found = true
	}
	if !found {
		return errors.New("expected VM change missing from plan")
	}
	return nil
}

func merge(existing map[string]VM, name string, vm VM) (map[string]VM, error) {
	if _, ok := existing[name]; ok {
		return nil, errors.New("VM name already exists")
	}
	result := map[string]VM{}
	for key, value := range existing {
		if value.ID == vm.ID {
			return nil, errors.New("VM ID already exists")
		}
		result[key] = value
	}
	result[name] = vm
	return result, nil
}

type Engine interface {
	load(context.Context) (map[string]VM, error)
	apply(context.Context, map[string]VM, string, string) error
	power(context.Context, VM, string) error
}

type Terraform struct {
	dir, endpoint, token string
	client               *http.Client
}

func (t *Terraform) run(ctx context.Context, args ...string) ([]byte, error) {
	command := exec.CommandContext(ctx, "terraform", args...)
	command.Dir = t.dir
	command.Env = append(os.Environ(), "TF_IN_AUTOMATION=1", "TF_INPUT=0", "TF_VAR_endpoint="+t.endpoint)
	output, err := command.CombinedOutput()
	if err != nil {
		// Provider diagnostics may contain infrastructure details. Keep them on disk.
		_ = os.WriteFile(filepath.Join(t.dir, "last-error.txt"), output, 0600)
		return nil, errors.New("Terraform failed; inspect infra/last-error.txt")
	}
	return output, nil
}

func (t *Terraform) load(ctx context.Context) (map[string]VM, error) {
	data, err := os.ReadFile(filepath.Join(t.dir, "desired.auto.tfvars.json"))
	inventory := Inventory{VMs: map[string]VM{}}
	if err == nil {
		if err := json.Unmarshal(data, &inventory); err != nil {
			return nil, err
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	if inventory.VMs == nil {
		return nil, errors.New("invalid desired inventory")
	}
	show, err := t.run(ctx, "show", "-json")
	if err != nil {
		return nil, err
	}
	var state struct {
		Values struct {
			Root struct {
				Resources []struct {
					Address, Type string
					Values        struct {
						Name string
						ID   int    `json:"vm_id"`
						Node string `json:"node_name"`
					}
				} `json:"resources"`
				Children []json.RawMessage `json:"child_modules"`
			} `json:"root_module"`
		} `json:"values"`
	}
	if err := json.Unmarshal(show, &state); err != nil {
		return nil, err
	}
	if len(state.Values.Root.Children) != 0 {
		return nil, errors.New("use a dedicated Forge workspace without child modules")
	}
	seen := map[string]bool{}
	for _, resource := range state.Values.Root.Resources {
		name := resource.Values.Name
		vm, ok := inventory.VMs[name]
		if !ok || resource.Type != "proxmox_virtual_environment_vm" || resource.Address != "proxmox_virtual_environment_vm.vm["+strconv.Quote(name)+"]" || vm.ID != resource.Values.ID || vm.Node != resource.Values.Node {
			return nil, errors.New("state and desired inventory disagree; reconcile before another operation")
		}
		seen[name] = true
	}
	if len(seen) != len(inventory.VMs) {
		return nil, errors.New("an earlier apply is incomplete; reconcile Terraform first")
	}
	return inventory.VMs, nil
}

func (t *Terraform) apply(ctx context.Context, vms map[string]VM, name, action string) error {
	data, err := json.MarshalIndent(Inventory{VMs: vms}, "", "  ")
	if err != nil {
		return err
	}
	candidate := filepath.Join(t.dir, "candidate.tfvars.json")
	if err := os.WriteFile(candidate, data, 0600); err != nil {
		return err
	}
	defer os.Remove(candidate)
	planPath := filepath.Join(t.dir, "forge.plan")
	defer os.Remove(planPath)
	if _, err := t.run(ctx, "plan", "-input=false", "-lock-timeout=10s", "-var-file=candidate.tfvars.json", "-out=forge.plan"); err != nil {
		return err
	}
	plan, err := t.run(ctx, "show", "-json", "forge.plan")
	if err != nil {
		return err
	}
	if err := checkPlan(plan, name, action); err != nil {
		return err
	}
	// Preserve the full desired configuration even if apply partially succeeds.
	if err := os.Rename(candidate, filepath.Join(t.dir, "desired.auto.tfvars.json")); err != nil {
		return err
	}
	_, err = t.run(ctx, "apply", "-input=false", "-lock-timeout=10s", "forge.plan")
	return err
}

func (t *Terraform) power(ctx context.Context, vm VM, action string) error {
	if action != "start" && action != "shutdown" {
		return errors.New("invalid power action")
	}
	endpoint := strings.TrimRight(t.endpoint, "/") + fmt.Sprintf("/api2/json/nodes/%s/qemu/%d/status/%s", url.PathEscape(vm.Node), vm.ID, action)
	body := ""
	if action == "shutdown" {
		body = "forceStop=0"
	}
	request, err := http.NewRequestWithContext(ctx, "POST", endpoint, strings.NewReader(body))
	if err != nil {
		return err
	}
	request.Header.Set("Authorization", "PVEAPIToken="+t.token)
	request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	response, err := t.client.Do(request)
	if err != nil {
		return errors.New("Proxmox connection failed; check address and CA trust")
	}
	defer response.Body.Close()
	_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 1<<20))
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return fmt.Errorf("Proxmox returned HTTP %d", response.StatusCode)
	}
	return nil
}

type Demo struct{ vms map[string]VM }

func (d *Demo) load(context.Context) (map[string]VM, error) {
	result := map[string]VM{}
	for k, v := range d.vms {
		result[k] = v
	}
	return result, nil
}
func (d *Demo) apply(ctx context.Context, vms map[string]VM, name, action string) error {
	d.vms = vms
	return nil
}
func (d *Demo) power(context.Context, VM, string) error { return nil }

func liveEngine(config Config) (*Terraform, error) {
	endpoint := os.Getenv("PROXMOX_VE_ENDPOINT")
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Scheme != "https" || parsed.Hostname() == "" || parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" || (parsed.Path != "" && parsed.Path != "/") {
		return nil, errors.New("set PROXMOX_VE_ENDPOINT to an HTTPS origin")
	}
	token := os.Getenv("PROXMOX_VE_API_TOKEN")
	if token == "" {
		return nil, errors.New("set PROXMOX_VE_API_TOKEN")
	}
	dir, err := filepath.Abs(config.Directory)
	if err != nil {
		return nil, err
	}
	return &Terraform{dir: dir, endpoint: endpoint, token: token, client: &http.Client{Timeout: 15 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}, nil
}
