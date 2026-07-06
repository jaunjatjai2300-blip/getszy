---
name: Legacy-getszy mobile nav pattern
description: How mobile hamburger nav was added to AdminLayout/DashboardLayout without duplicating nav markup
---

`AdminLayout.jsx` and `DashboardLayout.jsx` originally rendered their sidebar `<nav>` only inside `hidden md:flex` asides, with no way to reach it on mobile — the `md:hidden` header row only had a logo, no menu trigger.

**Fix pattern used:** extract the sidebar's inner JSX (header block + nav links + footer buttons) into a local `NavContent({ onNavigate })` component defined inside the layout function (so it closes over the same `open`/`toggle` state), then render it twice: once directly inside the desktop `<aside>`, and once inside a `Sheet`/`SheetContent` (shadcn) triggered by a `Menu` icon button in the mobile header row. Each `NavLink`'s `onClick` calls `onNavigate` (which closes the sheet) in addition to navigating.

**Why:** avoids maintaining two copies of the nav item list/markup, and matches the existing mobile-menu pattern already used in the storefront `Header.jsx` (which uses the same `Sheet` component).

**How to apply:** any other full-page layout in this app with a `hidden md:flex` sidebar and no mobile equivalent should follow the same `NavContent` extraction + `Sheet` pattern rather than writing a separate mobile nav from scratch. Remember `useState` calls must stay above any early `return` (e.g. the `loading`/`!user` guards) to avoid violating Rules of Hooks.
