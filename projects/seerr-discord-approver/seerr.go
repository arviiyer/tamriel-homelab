package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type Request struct {
	ID     int64  `json:"id"`
	Status int    `json:"status"`
	Type   string `json:"type"`
	Media  struct {
		TMDBID int64 `json:"tmdbId"`
	} `json:"media"`
}

type Seerr struct {
	mu                    sync.Mutex
	base, email, password string
	client                *http.Client
	cookies               map[string]*http.Cookie
	loggedIn              bool
}

func newSeerr(base, email, password string) *Seerr {
	return &Seerr{base: strings.TrimRight(base, "/"), email: email, password: password,
		cookies: map[string]*http.Cookie{}, client: &http.Client{Timeout: 10 * time.Second,
			CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}
}

func (s *Seerr) raw(ctx context.Context, method, path string, body any, output any) (int, error) {
	var reader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return 0, err
		}
		reader = bytes.NewReader(data)
	}
	r, err := http.NewRequestWithContext(ctx, method, s.base+"/api/v1"+path, reader)
	if err != nil {
		return 0, err
	}
	r.Header.Set("Content-Type", "application/json")
	for _, cookie := range s.cookies {
		r.AddCookie(cookie)
	}
	if method != "GET" {
		if c := s.cookies["XSRF-TOKEN"]; c != nil {
			token, err := url.QueryUnescape(c.Value)
			if err != nil {
				return 0, err
			}
			r.Header.Set("X-XSRF-TOKEN", token)
		}
	}
	response, err := s.client.Do(r)
	if err != nil {
		return 0, errors.New("Seerr connection failed")
	}
	defer response.Body.Close()
	for _, cookie := range response.Cookies() {
		if cookie.MaxAge < 0 {
			delete(s.cookies, cookie.Name)
		} else {
			s.cookies[cookie.Name] = cookie
		}
	}
	data, err := io.ReadAll(io.LimitReader(response.Body, (1<<20)+1))
	if err != nil || len(data) > 1<<20 {
		return response.StatusCode, errors.New("invalid Seerr response size")
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return response.StatusCode, fmt.Errorf("Seerr returned HTTP %d", response.StatusCode)
	}
	if output != nil {
		err = json.Unmarshal(data, output)
	}
	return response.StatusCode, err
}

func (s *Seerr) login(ctx context.Context) error {
	s.loggedIn = false
	s.cookies = map[string]*http.Cookie{}
	if _, err := s.raw(ctx, "GET", "/settings/public", nil, nil); err != nil {
		return err
	}
	if _, err := s.raw(ctx, "POST", "/auth/local", map[string]string{"email": s.email, "password": s.password}, nil); err != nil {
		return err
	}
	var user struct {
		Permissions int `json:"permissions"`
	}
	if _, err := s.raw(ctx, "GET", "/auth/me", nil, &user); err != nil {
		return err
	}
	if user.Permissions != 16 {
		return errors.New("Seerr account must have exactly Manage Requests (16)")
	}
	s.loggedIn = true
	return nil
}

func (s *Seerr) call(ctx context.Context, method, path string, output any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.loggedIn {
		if err := s.login(ctx); err != nil {
			return err
		}
	}
	status, err := s.raw(ctx, method, path, nil, output)
	if status == 401 || status == 403 {
		s.loggedIn = false
		// Only reads are retried. A later click reads current state before another write.
		if method == "GET" {
			if err := s.login(ctx); err != nil {
				return err
			}
			_, err = s.raw(ctx, method, path, nil, output)
		}
	}
	return err
}

func (s *Seerr) get(ctx context.Context, id int64) (Request, error) {
	var r Request
	err := s.call(ctx, "GET", fmt.Sprintf("/request/%d", id), &r)
	if err == nil && r.ID != id {
		err = errors.New("Seerr request ID mismatch")
	}
	return r, err
}

func (s *Seerr) pending(ctx context.Context) ([]Request, error) {
	var all []Request
	for skip := 0; skip < 1000; skip += 100 {
		var page struct {
			Results []Request `json:"results"`
		}
		if err := s.call(ctx, "GET", fmt.Sprintf("/request?take=100&skip=%d&filter=pending", skip), &page); err != nil {
			return nil, err
		}
		all = append(all, page.Results...)
		if len(page.Results) < 100 {
			return all, nil
		}
	}
	return nil, errors.New("more than 999 pending requests")
}

func (s *Seerr) title(ctx context.Context, r Request) (string, error) {
	if (r.Type != "movie" && r.Type != "tv") || r.Media.TMDBID <= 0 {
		return "", errors.New("unsupported media")
	}
	var detail struct{ Title, Name string }
	if err := s.call(ctx, "GET", fmt.Sprintf("/%s/%d", r.Type, r.Media.TMDBID), &detail); err != nil {
		return "", err
	}
	if detail.Title != "" {
		return detail.Title, nil
	}
	return detail.Name, nil
}

func (s *Seerr) decide(ctx context.Context, id int64, action string) (Request, error) {
	if action != "approve" && action != "decline" {
		return Request{}, errors.New("invalid action")
	}
	var r Request
	err := s.call(ctx, "POST", fmt.Sprintf("/request/%d/%s", id, action), &r)
	expected := 2
	if action == "decline" {
		expected = 3
	}
	if err == nil && (r.ID != id || r.Status != expected) {
		err = errors.New("unexpected decision response")
	}
	return r, err
}
