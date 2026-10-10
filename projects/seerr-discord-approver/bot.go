package main

import (
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/bwmarrin/discordgo"
)

type Record struct {
	ID                    int64
	Status                int
	Message, Title, Nonce string
	Expires               int64
	Synced                bool
}

type mediaAPI interface {
	get(context.Context, int64) (Request, error)
	pending(context.Context) ([]Request, error)
	title(context.Context, Request) (string, error)
	decide(context.Context, int64, string) (Request, error)
}

type Bot struct {
	mu                           sync.Mutex
	api                          mediaAPI
	discord                      *discordgo.Session
	guild, channel, owner, state string
	key                          []byte
	records                      map[int64]Record
}

func (b *Bot) load() error {
	b.records = map[int64]Record{}
	data, err := os.ReadFile(b.state)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, &b.records); err != nil {
		return err
	}
	if b.records == nil {
		return errors.New("invalid state: null")
	}
	for id, r := range b.records {
		if id <= 0 || r.ID != id || r.Message == "" || r.Nonce == "" {
			return errors.New("invalid stored request")
		}
	}
	return nil
}

func (b *Bot) save() error {
	if err := os.MkdirAll(filepath.Dir(b.state), 0700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(b.records, "", "  ")
	if err != nil {
		return err
	}
	file, err := os.CreateTemp(filepath.Dir(b.state), ".state-*")
	if err != nil {
		return err
	}
	defer os.Remove(file.Name())
	_, writeErr := file.Write(data)
	syncErr := file.Sync()
	closeErr := file.Close()
	if err := errors.Join(writeErr, syncErr, closeErr); err != nil {
		return err
	}
	return os.Rename(file.Name(), b.state)
}

func (b *Bot) sign(action string, r Record) string {
	value := fmt.Sprintf("%s:%d:%d:%s", action, r.ID, r.Expires, r.Nonce)
	mac := hmac.New(sha256.New, b.key)
	mac.Write([]byte(value))
	return value + ":" + base64.RawURLEncoding.EncodeToString(mac.Sum(nil)[:16])
}

func (b *Bot) verify(value string, now time.Time) (string, Record, error) {
	parts := strings.Split(value, ":")
	if len(parts) != 5 {
		return "", Record{}, errors.New("invalid action")
	}
	id, err := strconv.ParseInt(parts[1], 10, 64)
	if err != nil {
		return "", Record{}, err
	}
	r, ok := b.records[id]
	validAction := parts[0] == "approve" || parts[0] == "deny" || parts[0] == "decline" || parts[0] == "cancel"
	if !ok || !validAction || r.Status != 1 || now.Unix() >= r.Expires || !hmac.Equal([]byte(value), []byte(b.sign(parts[0], r))) {
		return "", Record{}, errors.New("expired or superseded action")
	}
	return parts[0], r, nil
}

func (b *Bot) allowed(i *discordgo.Interaction) bool {
	return i != nil && i.GuildID == b.guild && i.ChannelID == b.channel && i.Member != nil && i.Member.User != nil && i.Member.User.ID == b.owner
}

func (b *Bot) components(r Record, confirmation bool) []discordgo.MessageComponent {
	if r.Status != 1 {
		return []discordgo.MessageComponent{}
	}
	first, second, label := "approve", "deny", "Approve"
	style := discordgo.SuccessButton
	if confirmation {
		first, second, label, style = "decline", "cancel", "Confirm denial", discordgo.DangerButton
	}
	secondLabel := "Deny"
	if confirmation {
		secondLabel = "Cancel"
	}
	return []discordgo.MessageComponent{discordgo.ActionsRow{Components: []discordgo.MessageComponent{
		discordgo.Button{Label: label, Style: style, CustomID: b.sign(first, r)},
		discordgo.Button{Label: secondLabel, Style: discordgo.SecondaryButton, CustomID: b.sign(second, r)},
	}}}
}

func content(r Record) string {
	status := map[int]string{1: "Pending", 2: "Approved", 3: "Denied"}[r.Status]
	if status == "" {
		status = "Handled in Seerr"
	}
	// JSON quoting makes control characters visible; mentions are separately disabled.
	title := []rune(r.Title)
	if len(title) > 200 {
		title = title[:200]
	}
	return fmt.Sprintf("Seerr request #%d\n%s\n**%s**", r.ID, strconv.Quote(string(title)), status)
}

func (b *Bot) syncRecord(ctx context.Context, request Request) error {
	r, exists := b.records[request.ID]
	if !exists && request.Status != 1 {
		return nil
	}
	if !exists || (request.Status == 1 && (r.Status != 1 || r.Expires <= time.Now().Unix())) {
		title, err := b.api.title(ctx, request)
		if err != nil {
			return err
		}
		nonce := make([]byte, 8)
		if _, err := rand.Read(nonce); err != nil {
			return err
		}
		r = Record{ID: request.ID, Status: 1, Title: title, Nonce: base64.RawURLEncoding.EncodeToString(nonce), Expires: time.Now().Add(30 * 24 * time.Hour).Unix()}
		message, err := b.discord.ChannelMessageSendComplex(b.channel, &discordgo.MessageSend{
			Content: content(r), Components: b.components(r, false), AllowedMentions: &discordgo.MessageAllowedMentions{},
		}, discordgo.WithContext(ctx))
		if err != nil {
			return errors.New("Discord message send failed")
		}
		r.Message, r.Synced = message.ID, true
		previous, hadPrevious := b.records[r.ID]
		b.records[r.ID] = r
		if err := b.save(); err != nil {
			if hadPrevious {
				b.records[r.ID] = previous
			} else {
				delete(b.records, r.ID)
			}
			_ = b.discord.ChannelMessageDelete(b.channel, r.Message, discordgo.WithContext(ctx))
			return err
		}
		return nil
	}
	if r.Status != request.Status {
		r.Status, r.Synced = request.Status, false
		b.records[r.ID] = r
	}
	// Persist terminal status before editing Discord; reconciliation retries a failed edit.
	if !r.Synced {
		if err := b.save(); err != nil {
			return err
		}
		text, components := content(r), b.components(r, false)
		_, err := b.discord.ChannelMessageEditComplex(&discordgo.MessageEdit{ID: r.Message, Channel: b.channel,
			Content: &text, Components: &components, AllowedMentions: &discordgo.MessageAllowedMentions{}}, discordgo.WithContext(ctx))
		if err != nil {
			return errors.New("Discord status update pending")
		}
		r.Synced = true
		b.records[r.ID] = r
		return b.save()
	}
	return nil
}

func (b *Bot) reconcile(ctx context.Context) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	requests, err := b.api.pending(ctx)
	if err != nil {
		return err
	}
	for _, r := range requests {
		if err := b.syncRecord(ctx, r); err != nil {
			return err
		}
	}
	for id, r := range b.records {
		if r.Status != 1 && r.Synced {
			continue
		}
		current, err := b.api.get(ctx, id)
		if err != nil {
			return err
		}
		if err := b.syncRecord(ctx, current); err != nil {
			return err
		}
	}
	return nil
}

// Caller holds mu; every decision re-reads Seerr, including after a timeout.
func (b *Bot) decide(ctx context.Context, id int64, action string) (Request, error) {
	current, err := b.api.get(ctx, id)
	if err != nil {
		return Request{}, err
	}
	if current.Status != 1 {
		return current, nil
	}
	return b.api.decide(ctx, id, action)
}

func (b *Bot) interaction(s *discordgo.Session, event *discordgo.InteractionCreate) {
	if event == nil || event.Interaction == nil || event.Type != discordgo.InteractionMessageComponent {
		return
	}
	i := event.Interaction
	respond := func(text string, components []discordgo.MessageComponent) {
		_ = s.InteractionRespond(i, &discordgo.InteractionResponse{Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{Content: text, Flags: discordgo.MessageFlagsEphemeral, Components: components, AllowedMentions: &discordgo.MessageAllowedMentions{}}})
	}
	if !b.allowed(i) {
		respond("You are not the configured approver.", nil)
		return
	}
	// Acknowledge before waiting on network I/O or another decision.
	response := &discordgo.InteractionResponse{Type: discordgo.InteractionResponseDeferredChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{Flags: discordgo.MessageFlagsEphemeral}}
	customID := i.MessageComponentData().CustomID
	if strings.HasPrefix(customID, "cancel:") || strings.HasPrefix(customID, "decline:") {
		// Edit the confirmation itself, removing its buttons after cancel/confirm.
		response = &discordgo.InteractionResponse{Type: discordgo.InteractionResponseDeferredMessageUpdate}
	}
	if err := s.InteractionRespond(i, response); err != nil {
		return
	}
	edit := func(text string, components []discordgo.MessageComponent) {
		if components == nil {
			components = []discordgo.MessageComponent{}
		}
		_, _ = s.InteractionResponseEdit(i, &discordgo.WebhookEdit{Content: &text, Components: &components, AllowedMentions: &discordgo.MessageAllowedMentions{}})
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	action, record, err := b.verify(i.MessageComponentData().CustomID, time.Now())
	if err != nil {
		edit("This action has expired or the request was already handled.", nil)
		return
	}
	if (action == "approve" || action == "deny") && (i.Message == nil || i.Message.ID != record.Message) {
		edit("This is not the current request message.", nil)
		return
	}
	if action == "deny" {
		edit(fmt.Sprintf("Deny request #%d?", record.ID), b.components(record, true))
		return
	}
	if action == "cancel" {
		edit("Denial cancelled.", nil)
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	current, err := b.decide(ctx, record.ID, action)
	if err != nil {
		edit("Could not confirm the result. Check the request in Seerr before trying again.", nil)
		return
	}
	if err := b.syncRecord(ctx, current); err != nil {
		edit("Seerr handled the request. The Discord status update is pending.", nil)
		return
	}
	edit(content(b.records[record.ID]), nil)
}
