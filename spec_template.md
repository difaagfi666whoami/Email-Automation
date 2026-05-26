# spec_template.md — HTML Template Visual Specification

## Reference

The rendered PNG must visually match the Thunderbird email screenshots provided by
the user. The 7 reference images show:

- White background, full width
- Header block at top with sender info and action buttons
- Bold subject line
- Horizontal separator
- Monospaced plain-text body below

This file defines every visual element of `templates/email_view.html`.

---

## Page layout

```
┌──────────────────────────────────────────────────────────────┐  ← white bg
│  HEADER BLOCK                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [D]  Sender Name (bold)           [Reply][Reply All] │   │
│  │      sender@email.com (grey)      [Forward][Archive] │   │
│  │                                                      │   │
│  │ To  recipient1@... recipient2@... [MORE]             │   │
│  │ Reply to  replyto@...                                │   │
│  │                                                      │   │
│  │ Subject Line in Bold Large Font                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ─────────────────────────────────────────────────────────  │  ← <hr>
│  BODY BLOCK                                                  │
│  (monospaced text, whitespace preserved)                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Dimensions

| Property | Value |
|---|---|
| Page width | `900px` fixed (set by Playwright viewport) |
| Body font size | `13px` |
| Body line height | `1.5` |
| Outer padding | `20px` on all sides |
| Background | `#ffffff` |
| No dark mode | Template is always rendered light |

---

## Header block — sender row

### Avatar circle
- Grey filled circle, `40px × 40px`, `border-radius: 50%`
- Background: `#d0d0d0`
- Single letter: first letter of sender name, uppercased
- Font: 18px, bold, white, centered
- Floated left or flex item

### Sender name
- Text: value of `{{ sender_name }}`
- Font: 14px, `font-weight: 600`
- Color: `#1a1a1a`

### Sender email
- Text: value of `{{ sender_email }}`
- Font: 12px, `font-weight: 400`
- Color: `#666666`

### Action buttons (top right, same row as avatar)
- Four buttons: `Reply`, `Reply All ∨`, `Forward`, `Archive`
- Style: outlined, `border: 1px solid #cccccc`, `border-radius: 4px`
- Background: `#ffffff`
- Font: 12px, color `#333333`
- Padding: `4px 10px`
- Gap between buttons: `6px`
- NOT functional — purely visual decoration
- `Reply All` has a small downward chevron `∨` after the text

---

## Header block — recipients row

- Label `To` in grey (`#888888`), 12px, followed by recipient addresses
- Show first `{{ recipient_preview_count }}` (default 3) recipients inline, separated
  by comma and space
- After the preview list: a blue pill badge `MORE`
  - Background: `#2563eb`, color: `#ffffff`, border-radius: `4px`
  - Font: 11px, padding: `2px 6px`
  - Only shown if total recipients > `recipient_preview_count`

---

## Header block — reply-to row

- Label `Reply to` in grey (`#888888`), 12px
- Followed by `{{ reply_to }}` address in `#333333`

---

## Header block — subject line

- Text: `{{ subject }}`
- Font: `18px`, `font-weight: 700`
- Color: `#1a1a1a`
- Margin top: `12px`, margin bottom: `4px`
- No border, no background

---

## Separator

- `<hr>` element
- Style: `border: none; border-top: 1px solid #e0e0e0; margin: 12px 0;`

---

## Body block

### If body is plain text (`body_html` is None)

Wrap in:
```html
<pre style="
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #1a1a1a;
  white-space: pre;
  overflow-x: auto;
  margin: 0;
  padding: 0;
">{{ body_text }}</pre>
```

Key requirements:
- `white-space: pre` — preserves all spaces, tabs, newlines exactly as in the raw email
- `overflow-x: auto` — allows horizontal scroll for wide tables, no line wrapping
- Monospace font — column alignment in CSV-style tables must be preserved

### If body is HTML (`body_html` is not None)

Render inside a sandboxed `<div>`:
```html
<div style="
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  line-height: 1.5;
  color: #1a1a1a;
">{{ body_html | safe }}</div>
```

---

## Full Jinja2 template structure

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 13px;
      background: #ffffff;
      color: #1a1a1a;
      padding: 20px;
      width: 900px;
    }
    .header { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; }
    .avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: #d0d0d0; color: #fff;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px; font-weight: 700; flex-shrink: 0;
    }
    .sender-info { flex: 1; }
    .sender-name { font-size: 14px; font-weight: 600; color: #1a1a1a; }
    .sender-email { font-size: 12px; color: #666666; margin-top: 1px; }
    .action-buttons { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }
    .btn {
      border: 1px solid #cccccc; border-radius: 4px;
      background: #ffffff; font-size: 12px; color: #333333;
      padding: 4px 10px; cursor: default;
    }
    .meta { font-size: 12px; color: #888888; margin: 4px 0 2px; }
    .meta span { color: #333333; }
    .badge-more {
      display: inline-block; background: #2563eb; color: #ffffff;
      border-radius: 4px; font-size: 11px; padding: 2px 6px;
      margin-left: 4px; vertical-align: middle;
    }
    .subject { font-size: 18px; font-weight: 700; color: #1a1a1a; margin-top: 12px; }
    hr { border: none; border-top: 1px solid #e0e0e0; margin: 12px 0; }
    pre {
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px; line-height: 1.5; color: #1a1a1a;
      white-space: pre; overflow-x: auto;
    }
  </style>
</head>
<body>

  <div class="header">
    <div class="avatar">{{ sender_name[0].upper() }}</div>
    <div class="sender-info">
      <div class="sender-name">{{ sender_name }}</div>
      <div class="sender-email">{{ sender_email }}</div>
    </div>
    <div class="action-buttons">
      <span class="btn">↩ Reply</span>
      <span class="btn">↩↩ Reply All ∨</span>
      <span class="btn">↪ Forward</span>
      <span class="btn">⬚ Archive</span>
    </div>
  </div>

  <div class="meta">
    To&nbsp;&nbsp;
    {% for r in recipients[:recipient_preview_count] %}
      <span>{{ r }}</span>{% if not loop.last %}, {% endif %}
    {% endfor %}
    {% if recipients | length > recipient_preview_count %}
      <span class="badge-more">MORE</span>
    {% endif %}
  </div>

  <div class="meta">
    Reply to&nbsp;&nbsp;<span>{{ reply_to }}</span>
  </div>

  <div class="subject">{{ subject }}</div>

  <hr>

  {% if body_html %}
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                font-size:13px;line-height:1.5;color:#1a1a1a;">
      {{ body_html | safe }}
    </div>
  {% else %}
    <pre>{{ body_text }}</pre>
  {% endif %}

</body>
</html>
```

---

## What the rendered PNG must NOT contain

- No dark background
- No Thunderbird window chrome (tabs, toolbar, status bar) — email content only
- No Claude.ai or automation watermarks
- No scroll bars
- No truncated content — full page screenshot captures the entire body

---

## Validation checklist

Before accepting the rendered PNG as correct, verify:

- [ ] Avatar circle present with correct letter
- [ ] Sender name bold, sender email grey below it
- [ ] Four action buttons visible top-right
- [ ] `To:` row shows recipients with `MORE` badge if > 3
- [ ] `Reply to:` row present
- [ ] Subject line large and bold
- [ ] Horizontal separator between header and body
- [ ] Body text in monospace font with column alignment preserved
- [ ] White background, no clipping of content
- [ ] PNG width matches 900px viewport
