package main

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"flag"
	"html/template"
	"log"
	"net"
	"net/http"
	"os"
	"regexp"
	"slices"
	"strconv"
	"sync"
	"time"
)

//go:embed index.html
var page string
var namePattern = regexp.MustCompile(`^[a-z][a-z0-9-]{0,39}$`)
var view = template.Must(template.New("forge").Parse(page))

type Portal struct {
	mu           sync.Mutex
	engine       Engine
	config       Config
	csrf, result string
	demo, busy   bool
}

func (p *Portal) handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", p.index)
	mux.HandleFunc("POST /action", p.action)
	protected := http.NewCrossOriginProtection().Handler(mux)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, _, err := net.SplitHostPort(r.Host)
		if err != nil {
			host = r.Host
		}
		if host != "127.0.0.1" && host != "localhost" && host != "::1" {
			http.Error(w, "use the loopback address", 403)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
		protected.ServeHTTP(w, r)
	})
}

func (p *Portal) index(w http.ResponseWriter, r *http.Request) {
	p.mu.Lock()
	defer p.mu.Unlock()
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	var vms map[string]VM
	message := p.result
	if !p.busy {
		var err error
		vms, err = p.engine.load(ctx)
		if err != nil {
			message = err.Error()
		}
	}
	_ = view.Execute(w, map[string]any{"VMs": vms, "Config": p.config, "CSRF": p.csrf, "Result": message, "Busy": p.busy, "Demo": p.demo})
}

func (p *Portal) action(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 8192)
	if r.ParseForm() != nil || subtle.ConstantTimeCompare([]byte(r.FormValue("csrf")), []byte(p.csrf)) != 1 {
		http.Error(w, "invalid form", 403)
		return
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.busy {
		http.Error(w, "another operation is running", 409)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	vms, err := p.engine.load(ctx)
	if err != nil {
		http.Error(w, err.Error(), 409)
		return
	}
	name, action := r.FormValue("name"), r.FormValue("action")
	vm, exists := vms[name]
	switch action {
	case "launch":
		id, err := strconv.Atoi(r.FormValue("id"))
		node := r.FormValue("node")
		tpl, ok := p.config.Templates[r.FormValue("template")]
		size, sizeOK := p.config.Sizes[r.FormValue("size")]
		if err != nil || id < 100 || id > 999999 || !namePattern.MatchString(name) || !ok || !sizeOK || !slices.Contains(p.config.Nodes, node) {
			http.Error(w, "invalid VM settings", 400)
			return
		}
		for _, template := range p.config.Templates {
			if id == template.ID {
				http.Error(w, "VM ID is a template", 409)
				return
			}
		}
		vm = VM{ID: id, Node: node, TemplateID: tpl.ID, TemplateNode: tpl.Node, Cores: size.Cores, Memory: size.Memory}
		vms, err = merge(vms, name, vm)
		if err != nil {
			http.Error(w, err.Error(), 409)
			return
		}
	case "destroy":
		if !exists || vm.Protected || r.FormValue("confirm") != name {
			http.Error(w, "VM must be unprotected and its name must match", 409)
			return
		}
		delete(vms, name)
	case "protect":
		if !exists {
			http.NotFound(w, r)
			return
		}
		vm.Protected = !vm.Protected
		vms[name] = vm
	case "start", "shutdown":
		if !exists {
			http.NotFound(w, r)
			return
		}
	default:
		http.Error(w, "unknown action", 400)
		return
	}
	p.busy, p.result = true, "Running "+action+" for "+name
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Minute)
		defer cancel()
		var err error
		if action == "start" || action == "shutdown" {
			err = p.engine.power(ctx, vm, action)
		} else {
			err = p.engine.apply(ctx, vms, name, action)
		}
		p.mu.Lock()
		defer p.mu.Unlock()
		p.busy = false
		p.result = "Completed " + action + " for " + name
		if action == "start" || action == "shutdown" {
			p.result = "Proxmox accepted " + action + " for " + name + ". Check its task result in Proxmox."
		}
		if p.demo {
			p.result = "Sample operation: " + action + " for " + name
		}
		if err != nil {
			p.result = err.Error()
		}
	}()
	http.Redirect(w, r, "/", http.StatusSeeOther)
}

func main() {
	demo := flag.Bool("demo", false, "Use sample inventory without Terraform or Proxmox")
	configPath := flag.String("config", "config.json", "Configuration file")
	flag.Parse()
	data, err := os.ReadFile(*configPath)
	if err != nil {
		log.Fatal(err)
	}
	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		log.Fatal(err)
	}
	if len(config.Nodes) == 0 || len(config.Templates) == 0 || len(config.Sizes) == 0 {
		log.Fatal("configure nodes, templates and sizes")
	}
	csrf := make([]byte, 32)
	if _, err := rand.Read(csrf); err != nil {
		log.Fatal(err)
	}
	p := &Portal{config: config, csrf: hex.EncodeToString(csrf), demo: *demo}
	if *demo {
		p.engine = &Demo{vms: map[string]VM{"apps-01": {ID: 201, Node: "pve-01", TemplateID: 9000, TemplateNode: "pve-01", Cores: 2, Memory: 4096, Protected: true}}}
	} else {
		engine, err := liveEngine(config)
		if err != nil {
			log.Fatal(err)
		}
		p.engine = engine
	}
	server := &http.Server{Addr: "127.0.0.1:8088", Handler: p.handler(), ReadHeaderTimeout: 3 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second}
	log.Print("Forge: http://127.0.0.1:8088")
	log.Fatal(server.ListenAndServe())
}
