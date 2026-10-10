package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestMergePreservesEveryExistingSetting(t *testing.T) {
	original := VM{ID: 201, Node: "pve-01", TemplateID: 9000, TemplateNode: "pve-01", Cores: 4, Memory: 8192, Protected: true}
	existing := map[string]VM{"apps-01": original}
	result, err := merge(existing, "test-01", VM{ID: 301, Node: "pve-01"})
	if err != nil || result["apps-01"] != original || len(existing) != 1 {
		t.Fatal(result, err)
	}
	if _, err := merge(existing, "apps-01", VM{ID: 302}); err == nil {
		t.Fatal("name conflict accepted")
	}
	if _, err := merge(existing, "test-01", VM{ID: 201}); err == nil {
		t.Fatal("ID conflict accepted")
	}
}

func TestPlanRejectsCollateralChanges(t *testing.T) {
	change := func(address string, actions ...string) map[string]any {
		return map[string]any{"address": address, "mode": "managed", "change": map[string]any{"actions": actions}}
	}
	target := `proxmox_virtual_environment_vm.vm["test-01"]`
	for _, check := range []struct {
		changes []map[string]any
		valid   bool
	}{
		{[]map[string]any{change(target, "create")}, true},
		{[]map[string]any{change(target, "delete", "create")}, false},
		{[]map[string]any{change(target, "create"), change(`proxmox_virtual_environment_vm.vm["apps-01"]`, "delete")}, false},
		{[]map[string]any{change(target, "create"), change(`proxmox_virtual_environment_vm.vm["apps-01"]`, "update")}, false},
		{nil, false},
	} {
		data, _ := json.Marshal(map[string]any{"resource_changes": check.changes})
		if (checkPlan(data, "test-01", "launch") == nil) != check.valid {
			t.Fatal(string(data))
		}
	}
}

func TestPortalRefusesProtectedDestroyAndCrossOrigin(t *testing.T) {
	p := &Portal{csrf: "fixture-csrf", engine: &Demo{vms: map[string]VM{"apps-01": {ID: 201, Protected: true}}}}
	form := url.Values{"csrf": {p.csrf}, "action": {"destroy"}, "name": {"apps-01"}, "confirm": {"apps-01"}}
	for _, origin := range []string{"", "https://example.com"} {
		r := httptest.NewRequest("POST", "http://127.0.0.1:8088/action", strings.NewReader(form.Encode()))
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		w := httptest.NewRecorder()
		p.handler().ServeHTTP(w, r)
		want := 409
		if origin != "" {
			want = 403
		}
		if w.Code != want {
			t.Fatal(w.Code, w.Body.String())
		}
	}
	vms, _ := p.engine.load(context.Background())
	if len(vms) != 1 {
		t.Fatal("protected VM removed")
	}
}

func TestPowerUsesGracefulShutdownAndDoesNotFollowRedirect(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api2/json/nodes/pve-01/qemu/301/status/shutdown" || r.Method != "POST" {
			t.Error(r.Method, r.URL.Path)
		}
		if r.FormValue("forceStop") != "0" {
			t.Error("forced stop enabled")
		}
		w.Header().Set("Location", "https://example.com/")
		w.WriteHeader(302)
	}))
	defer server.Close()
	engine := &Terraform{endpoint: server.URL, token: "fixture-token", client: &http.Client{CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}
	if err := engine.power(context.Background(), VM{ID: 301, Node: "pve-01"}, "shutdown"); err == nil {
		t.Fatal("redirect accepted")
	}
}

func TestStartDoesNotSendShutdownParameters(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api2/json/nodes/pve-01/qemu/301/status/start" {
			t.Error(r.URL.Path)
		}
		if r.FormValue("forceStop") != "" {
			t.Error("start received an unsupported shutdown parameter")
		}
		w.Write([]byte(`{"data":"sample-task"}`))
	}))
	defer server.Close()
	engine := &Terraform{endpoint: server.URL, token: "fixture-token", client: server.Client()}
	if err := engine.power(context.Background(), VM{ID: 301, Node: "pve-01"}, "start"); err != nil {
		t.Fatal(err)
	}
}
