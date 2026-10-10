package main

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/bwmarrin/discordgo"
)

type fakeMedia struct{ status, writes int }

func (f *fakeMedia) get(context.Context, int64) (Request, error) {
	return Request{ID: 42, Status: f.status}, nil
}
func (f *fakeMedia) pending(context.Context) ([]Request, error)     { return nil, nil }
func (f *fakeMedia) title(context.Context, Request) (string, error) { return "Example film", nil }
func (f *fakeMedia) decide(ctx context.Context, id int64, action string) (Request, error) {
	f.writes++
	f.status = 2
	if action == "decline" {
		f.status = 3
	}
	return Request{ID: id, Status: f.status}, nil
}

type transportFunc func(*http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func interactionFixture(t *testing.T) (*Bot, *fakeMedia, func(string, string) *discordgo.InteractionCreate, *[]string) {
	t.Helper()
	api := &fakeMedia{status: 1}
	session, _ := discordgo.New("Bot synthetic-token")
	var bodies []string
	session.Client = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
		data, _ := io.ReadAll(r.Body)
		bodies = append(bodies, string(data))
		return &http.Response{StatusCode: 200, Header: http.Header{}, Body: io.NopCloser(strings.NewReader(`{"id":"message-42"}`))}, nil
	})}
	r := Record{ID: 42, Status: 1, Message: "message-42", Title: "Example film", Nonce: "fixture-nonce", Expires: time.Now().Add(time.Hour).Unix(), Synced: true}
	b := &Bot{api: api, discord: session, guild: "1", channel: "2", owner: "3", key: []byte("synthetic signing material"), state: filepath.Join(t.TempDir(), "state.json"), records: map[int64]Record{42: r}}
	event := func(action, message string) *discordgo.InteractionCreate {
		return &discordgo.InteractionCreate{Interaction: &discordgo.Interaction{ID: "fixture-interaction", AppID: "fixture-app", Token: "synthetic-interaction-token", Type: discordgo.InteractionMessageComponent,
			GuildID: "1", ChannelID: "2", Member: &discordgo.Member{User: &discordgo.User{ID: "3"}}, Message: &discordgo.Message{ID: message},
			Data: discordgo.MessageComponentInteractionData{CustomID: b.sign(action, r)}}}
	}
	return b, api, event, &bodies
}

func TestApproveInteractionAndReplay(t *testing.T) {
	b, api, event, _ := interactionFixture(t)
	b.interaction(b.discord, event("approve", "wrong-message"))
	if api.writes != 0 {
		t.Fatal("wrong message accepted")
	}
	b.interaction(b.discord, event("approve", "message-42"))
	b.interaction(b.discord, event("approve", "message-42"))
	if api.writes != 1 || b.records[42].Status != 2 {
		t.Fatal("decision or replay handling failed")
	}
}

func TestDenyRequiresConfirmationAndCancelDoesNotWrite(t *testing.T) {
	b, api, event, bodies := interactionFixture(t)
	b.interaction(b.discord, event("deny", "message-42"))
	if api.writes != 0 || !strings.Contains(strings.Join(*bodies, "\n"), "Confirm denial") {
		t.Fatal("denial was not confirmed privately")
	}
	b.interaction(b.discord, event("cancel", "ephemeral-confirmation"))
	if api.writes != 0 {
		t.Fatal("cancel changed the request")
	}
	if !strings.Contains((*bodies)[len(*bodies)-2], `"type":6`) {
		t.Fatal("cancel must update the existing confirmation, not leave its buttons active")
	}
	b.interaction(b.discord, event("deny", "message-42"))
	b.interaction(b.discord, event("decline", "ephemeral-confirmation"))
	if api.writes != 1 || b.records[42].Status != 3 {
		t.Fatal("confirmed denial failed")
	}
}

func TestOwnerAndLocation(t *testing.T) {
	b := &Bot{guild: "1", channel: "2", owner: "3"}
	for _, check := range []struct {
		guild, channel, user string
		want                 bool
	}{{"1", "2", "3", true}, {"9", "2", "3", false}, {"1", "9", "3", false}, {"1", "2", "9", false}, {"", "2", "3", false}} {
		i := &discordgo.Interaction{GuildID: check.guild, ChannelID: check.channel, Member: &discordgo.Member{User: &discordgo.User{ID: check.user}}}
		if b.allowed(i) != check.want {
			t.Fatal(check)
		}
	}
	if b.allowed(nil) || b.allowed(&discordgo.Interaction{GuildID: "1", ChannelID: "2"}) {
		t.Fatal("missing member accepted")
	}
}

func TestSignedActionPersistenceAndExpiry(t *testing.T) {
	r := Record{ID: 42, Status: 1, Message: "fixture-message", Nonce: "fixture-nonce", Expires: time.Now().Add(time.Hour).Unix()}
	b := &Bot{key: []byte("fixture signing material"), state: filepath.Join(t.TempDir(), "state.json"), records: map[int64]Record{42: r}}
	value := b.sign("approve", r)
	if err := b.save(); err != nil {
		t.Fatal(err)
	}
	if err := b.load(); err != nil {
		t.Fatal(err)
	}
	if action, _, err := b.verify(value, time.Now()); err != nil || action != "approve" {
		t.Fatal(action, err)
	}
	for _, invalid := range []string{value + "x", strings.Replace(value, "approve", "decline", 1), b.sign("unknown", r)} {
		if _, _, err := b.verify(invalid, time.Now()); err == nil {
			t.Fatal("accepted tampered action")
		}
	}
	if _, _, err := b.verify(value, time.Now().Add(2*time.Hour)); err == nil {
		t.Fatal("accepted expired action")
	}
	r.Status = 2
	b.records[42] = r
	if _, _, err := b.verify(value, time.Now()); err == nil {
		t.Fatal("accepted completed request")
	}
}

func TestSeerrMutationIsNotRetriedAfterSessionExpiry(t *testing.T) {
	posts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/request/42/approve" {
			posts++
			w.WriteHeader(401)
			return
		}
		t.Fatal("unexpected retry or login", r.URL.Path)
	}))
	defer server.Close()
	s := newSeerr(server.URL, "approver@example.com", "synthetic password")
	s.loggedIn = true
	if _, err := s.decide(context.Background(), 42, "approve"); err == nil || posts != 1 || s.loggedIn {
		t.Fatal("mutation retry policy violated")
	}
}

func TestLoginChecksPermissionsAndCSRF(t *testing.T) {
	permission := 16
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/settings/public":
			http.SetCookie(w, &http.Cookie{Name: "XSRF-TOKEN", Value: "synthetic%20csrf"})
			w.Write([]byte(`{}`))
		case "/api/v1/auth/local":
			if r.Header.Get("X-XSRF-TOKEN") != "synthetic csrf" {
				t.Error("missing CSRF token")
			}
			w.Write([]byte(`{}`))
		case "/api/v1/auth/me":
			json.NewEncoder(w).Encode(map[string]int{"permissions": permission})
		default:
			t.Error("unexpected path", r.URL.Path)
		}
	}))
	defer server.Close()
	s := newSeerr(server.URL, "approver@example.com", "synthetic password")
	if err := s.login(context.Background()); err != nil {
		t.Fatal(err)
	}
	permission = 18
	if err := s.login(context.Background()); err == nil || s.loggedIn {
		t.Fatal("administrator accepted")
	}
}

func TestAlreadyHandledRequestDoesNotMutate(t *testing.T) {
	posts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" {
			posts++
		}
		w.Write([]byte(`{"id":42,"status":2}`))
	}))
	defer server.Close()
	s := newSeerr(server.URL, "approver@example.com", "synthetic password")
	s.loggedIn = true
	b := &Bot{api: s}
	r, err := b.decide(context.Background(), 42, "decline")
	if err != nil || r.Status != 2 || posts != 0 {
		t.Fatal("stale decision mutated Seerr")
	}
}

func TestWebhookAuthenticationAndPayload(t *testing.T) {
	var ready atomic.Bool
	ready.Store(true)
	calls := 0
	handler := webhook("fixture-secret", &ready, func(ctx context.Context, id int64) error {
		calls++
		if id != 42 {
			t.Error(id)
		}
		return nil
	})
	for _, check := range []struct {
		auth, body string
		want       int
	}{
		{"", `{"notification_type":"MEDIA_PENDING","request_id":42}`, 401},
		{"Bearer fixture-secret", `{"notification_type":"MEDIA_PENDING","request_id":"42"}`, 202},
		{"Bearer fixture-secret", `{"notification_type":"MEDIA_PENDING","request_id":42} {}`, 400},
		{"Bearer fixture-secret", `{"notification_type":"MEDIA_PENDING","request_id":-1}`, 400},
		{"Bearer fixture-secret", `{"notification_type":"OTHER","request_id":42}`, 400},
	} {
		r := httptest.NewRequest("POST", "/webhooks/seerr", strings.NewReader(check.body))
		r.Header.Set("Authorization", check.auth)
		r.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, r)
		if w.Code != check.want {
			t.Fatal(w.Code, check.want, w.Body.String())
		}
	}
	if calls != 1 {
		t.Fatal(calls)
	}
}
