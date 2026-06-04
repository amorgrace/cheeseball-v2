# CheeseBall Admin Dashboard — Design System

## Color Tokens

These are the official design tokens. Use CSS custom properties mapped from these values.

```
Primary Blue:      #1A6FFF
Blue Dark:         #1259D9   (hover/active states)
Blue Light:        #EEF3FF   (subtle blue backgrounds)

Text Primary:      #0A0F1E   (headings, body)
Text Secondary:    #6B7A99   (labels, muted text)
Text Tertiary:     #A8B4CC   (placeholders, disabled)

Border:            #E8EEFF   (dividers, card borders)
Surface:           #F7F9FF   (card/section backgrounds)
White:             #FFFFFF   (page background, card surface)

Success Green:     #00C48C
Green Light:       #E6FAF4   (success background)
Green Text:        #00966B   (success text)
Mint Green:        #4ADE80   (charts, accents)

Error Red:         #EF4444
Red Light:         #FEF2F2   (error background)
Red Text:          #B91C1C   (error text)
```

## CSS Custom Properties

```css
:root {
  /* Primary */
  --blue: #1A6FFF;
  --blue-dark: #1259D9;
  --blue-light: #EEF3FF;

  /* Text */
  --text: #0A0F1E;
  --text-2: #6B7A99;
  --text-3: #A8B4CC;

  /* Surfaces & Borders */
  --border: #E8EEFF;
  --surface: #F7F9FF;
  --white: #FFFFFF;

  /* Status: Success */
  --green: #00C48C;
  --green-light: #E6FAF4;
  --green-text: #00966B;
  --mint-green: #4ADE80;

  /* Status: Error */
  --red: #EF4444;
  --red-light: #FEF2F2;
  --red-text: #B91C1C;

  /* Status: Warning (derived) */
  --amber: #F59E0B;
  --amber-light: #FFFBEB;
  --amber-text: #B45309;

  /* Typography */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

  /* Spacing scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Border radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(10, 15, 30, 0.04);
  --shadow-md: 0 4px 12px rgba(10, 15, 30, 0.06);
  --shadow-lg: 0 8px 24px rgba(10, 15, 30, 0.08);
  --shadow-blue: 0 4px 14px rgba(26, 111, 255, 0.25);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 350ms ease;

  /* Sidebar */
  --sidebar-width: 260px;
  --sidebar-collapsed: 72px;
  --header-height: 64px;
}
```

## Theme: Light Professional

This is a **light theme** — clean, professional, fintech-grade. NOT a dark theme.

- **Page background**: `var(--surface)` (#F7F9FF) — very subtle blue-gray
- **Cards/Panels**: `var(--white)` with `var(--border)` borders and `var(--shadow-sm)`
- **Sidebar**: `var(--white)` background, `var(--blue)` for active item highlight
- **Header**: `var(--white)` with bottom border

## Typography

- **Font**: Inter (Google Fonts), fallback to system stack
- **Sizes**:
  - Page title: 24px / 700 weight
  - Section title: 18px / 600
  - Body: 14px / 400
  - Caption/Label: 12px / 500
  - Small: 11px / 400

## Component Patterns

### Cards
```css
.card {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-normal);
}
.card:hover {
  box-shadow: var(--shadow-md);
}
```

### Buttons
```css
/* Primary */
.btn-primary {
  background: var(--blue);
  color: var(--white);
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 20px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-primary:hover {
  background: var(--blue-dark);
  box-shadow: var(--shadow-blue);
}

/* Secondary (ghost) */
.btn-secondary {
  background: var(--blue-light);
  color: var(--blue);
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 20px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}
.btn-secondary:hover {
  background: #dce5ff;
}

/* Danger */
.btn-danger {
  background: var(--red);
  color: var(--white);
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 20px;
  font-weight: 600;
  cursor: pointer;
}
```

### Status Badges
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  gap: 4px;
}
.badge-success {
  background: var(--green-light);
  color: var(--green-text);
}
.badge-error {
  background: var(--red-light);
  color: var(--red-text);
}
.badge-warning {
  background: var(--amber-light);
  color: var(--amber-text);
}
.badge-info {
  background: var(--blue-light);
  color: var(--blue);
}
.badge-neutral {
  background: var(--surface);
  color: var(--text-2);
}
```

### Data Tables
```css
.table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}
.table th {
  background: var(--surface);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.table td {
  padding: 14px 16px;
  font-size: 14px;
  color: var(--text);
  border-bottom: 1px solid var(--border);
}
.table tr:hover td {
  background: var(--surface);
}
```

### Stats Cards (Dashboard)
```css
.stats-card {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.stats-card .label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.stats-card .value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}
.stats-card .change {
  font-size: 13px;
  font-weight: 600;
}
.stats-card .change.positive { color: var(--green-text); }
.stats-card .change.negative { color: var(--red-text); }
```

### Sidebar
```css
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--white);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: var(--space-6) 0;
  z-index: 100;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-6);
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all var(--transition-fast);
  border-left: 3px solid transparent;
}
.sidebar-item:hover {
  background: var(--surface);
  color: var(--text);
}
.sidebar-item.active {
  background: var(--blue-light);
  color: var(--blue);
  border-left-color: var(--blue);
  font-weight: 600;
}
```

### Input Fields
```css
.input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-family: var(--font-family);
  color: var(--text);
  background: var(--white);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.input::placeholder {
  color: var(--text-3);
}
.input:focus {
  outline: none;
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(26, 111, 255, 0.1);
}
```

### Modals
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 30, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--transition-fast);
}
.modal {
  background: var(--white);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  max-width: 480px;
  width: 90%;
  box-shadow: var(--shadow-lg);
  animation: slideUp var(--transition-normal);
}
```

## Layout

```
┌─────────────────────────────────────────────────┐
│ Sidebar (260px)  │  Header (64px)               │
│                  │──────────────────────────────│
│  Logo            │                              │
│  ─────           │   Main Content Area          │
│  Dashboard       │                              │
│  Users           │   (scrollable)               │
│  Transactions    │                              │
│  KYC             │                              │
│  Withdrawals     │                              │
│  Wallets         │                              │
│  Rates           │                              │
│  Reserves        │                              │
│  Quidax          │                              │
│                  │                              │
│  ─────           │                              │
│  Settings        │                              │
│  Logout          │                              │
└─────────────────────────────────────────────────┘
```

## Animation Patterns

- **Page transitions**: Subtle fade-in (opacity 0→1, translateY 8px→0, 250ms ease)
- **Card hover**: Elevation increase via box-shadow
- **Button press**: Scale 0.97 on active
- **Table row hover**: Background color shift
- **Modal**: Backdrop fade-in + content slide-up
- **Loading states**: Skeleton shimmer animation (gradient sweep)
- **Status badge**: No animation (static indicators)
- **Sidebar item**: Smooth color + background transition

## Responsive Breakpoints

- **Desktop**: > 1024px — full sidebar + content
- **Tablet**: 768px–1024px — collapsed sidebar (icons only) + content
- **Mobile**: < 768px — sidebar as overlay drawer
