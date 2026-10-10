package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"io"
	"log"
	"mime"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/bwmarrin/discordgo"
)

func secret(name string) string {
	data, err := os.ReadFile(os.Getenv(name + "_FILE"))
	if err != nil || len(strings.TrimSpace(string(data))) < 16 {
		log.Fatalf("%s_FILE must name a readable secret of at least 16 characters", name)
	}
	return strings.TrimSpace(string(data))
}

func identifier(name string) string {
	value := os.Getenv(name)
	id, err := strconv.ParseUint(value, 10, 64)
	if err != nil || id == 0 {
		log.Fatalf("Set %s to its Discord ID", name)
	}
	return value
}

type requestID int64

func (id *requestID) UnmarshalJSON(data []byte) error {
	text := string(data)
	if strings.HasPrefix(text, `"`) {
		if err := json.Unmarshal(data, &text); err != nil {
			return err
		}
	}
	n, err := strconv.ParseInt(text, 10, 64)
	if err != nil || n <= 0 {
		return errors.New("invalid request ID")
	}
	*id = requestID(n)
	return nil
}

func webhook(secret string, ready *atomic.Bool, changed func(context.Context, int64) error) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		if !ready.Load() {
			http.Error(w, "starting", 503)
			return
		}
		w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("POST /webhooks/seerr", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		if subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte("Bearer "+secret)) != 1 {
			http.Error(w, "unauthorized", 401)
			return
		}
		if !ready.Load() {
			http.Error(w, "starting", 503)
			return
		}
		kind, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if err != nil || kind != "application/json" {
			http.Error(w, "expected JSON", 415)
			return
		}
		var payload struct {
			Type string    `json:"notification_type"`
			ID   requestID `json:"request_id"`
		}
		decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096))
		decoder.DisallowUnknownFields()
		if decoder.Decode(&payload) != nil || decoder.Decode(&struct{}{}) != io.EOF || payload.ID <= 0 {
			http.Error(w, "invalid payload", 400)
			return
		}
		switch payload.Type {
		case "MEDIA_PENDING", "MEDIA_APPROVED", "MEDIA_AUTO_APPROVED", "MEDIA_DECLINED":
		default:
			http.Error(w, "unsupported event", 400)
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
		defer cancel()
		if changed(ctx, int64(payload.ID)) != nil {
			http.Error(w, "processing failed", 502)
			return
		}
		w.WriteHeader(202)
	})
	return mux
}

func main() {
	base := os.Getenv("SEERR_URL")
	parsed, err := url.Parse(base)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Hostname() == "" || parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" || (parsed.Path != "" && parsed.Path != "/") {
		log.Fatal("SEERR_URL must be an HTTP(S) origin without credentials")
	}
	email := os.Getenv("SEERR_EMAIL")
	if !strings.Contains(email, "@") {
		log.Fatal("Set SEERR_EMAIL")
	}
	session, err := discordgo.New("Bot " + secret("DISCORD_BOT_TOKEN"))
	if err != nil {
		log.Fatal("Discord configuration failed")
	}
	session.Identify.Intents = discordgo.IntentsGuilds
	session.Client.Timeout = 10 * time.Second
	session.ShouldRetryOnRateLimit = false
	state := os.Getenv("STATE_PATH")
	if state == "" {
		state = "data/state.json"
	}
	bot := &Bot{api: newSeerr(base, email, secret("SEERR_PASSWORD")), discord: session,
		guild: identifier("DISCORD_GUILD_ID"), channel: identifier("DISCORD_CHANNEL_ID"), owner: identifier("DISCORD_APPROVER_USER_ID"),
		state: state, key: []byte(secret("COMPONENT_SIGNING_KEY"))}
	if err := bot.load(); err != nil {
		log.Fatal("Cannot read state; restore it before restarting: ", err)
	}
	var ready atomic.Bool
	session.AddHandler(bot.interaction)
	session.AddHandler(func(*discordgo.Session, *discordgo.Ready) { ready.Store(true) })
	session.AddHandler(func(*discordgo.Session, *discordgo.Disconnect) { ready.Store(false) })
	session.AddHandler(func(*discordgo.Session, *discordgo.Resumed) { ready.Store(true) })
	if err := session.Open(); err != nil {
		log.Fatal("Discord connection failed")
	}
	defer session.Close()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	address := os.Getenv("LISTEN_ADDRESS")
	if address == "" {
		address = "127.0.0.1:8080"
	}
	server := &http.Server{Addr: address, ReadHeaderTimeout: 3 * time.Second, ReadTimeout: 5 * time.Second, WriteTimeout: 25 * time.Second, IdleTimeout: 30 * time.Second,
		Handler: webhook(secret("WEBHOOK_SECRET"), &ready, func(ctx context.Context, id int64) error {
			bot.mu.Lock()
			defer bot.mu.Unlock()
			current, err := bot.api.get(ctx, id)
			if err != nil {
				return err
			}
			return bot.syncRecord(ctx, current)
		})}
	go func() {
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Print("HTTP server failed")
			stop()
		}
	}()
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	for {
		cycle, cancel := context.WithTimeout(ctx, 50*time.Second)
		if err := bot.reconcile(cycle); err != nil && ctx.Err() == nil {
			log.Print("Reconciliation failed: ", err)
		}
		cancel()
		select {
		case <-ctx.Done():
			shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = server.Shutdown(shutdown)
			return
		case <-ticker.C:
		}
	}
}
