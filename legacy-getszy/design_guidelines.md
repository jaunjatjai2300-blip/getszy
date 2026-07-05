{
  "brand": {
    "name": "getszy",
    "positioning": "Premium feminine commerce + tech empowerment. Warm, trustworthy storefront; crisp, capable admin; magical AI command center.",
    "voice": {
      "tone": ["friendly", "confident", "women-empowering", "premium"],
      "copy_style": "Mostly English with subtle Hinglish helpers (short, not gimmicky).",
      "example_microcopy": {
        "hero_kicker": "Made for women who do it all",
        "hero_title": "Shop premium essentials. Learn AI. Run your business—without coding.",
        "hero_subtitle": "Fashion, beauty, kids, home + powerful digital tools. Admin dashboard with AI commands—type what you want, getszy does it.",
        "ai_chat_placeholder": "e.g., ‘Add 20 units of Rose Gold Earrings, price 799, category Jewellery’",
        "empty_state": "Abhi kuch nahi hai—let’s create your first item."
      }
    }
  },

  "gradient_restriction_rule": {
    "prohibited": [
      "NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.",
      "NEVER let gradients cover more than 20% of the viewport.",
      "NEVER apply gradients to text-heavy content or reading areas.",
      "NEVER use gradients on small UI elements (<100px width).",
      "NEVER stack multiple gradient layers in the same viewport.",
      "For AI chat/voice: do not use purple."
    ],
    "enforcement": "IF gradient area exceeds 20% of viewport OR impacts readability THEN fallback to solid colors or a single subtle two-color wash.",
    "allowed_usage": [
      "Hero section background wash (top 15–20% only)",
      "Decorative corner glows behind hero imagery",
      "Large CTA button background (>= 140px wide) with very subtle light gradient",
      "AI Chat header strip / subtle panel glow (not behind long text)"
    ]
  },

  "design_personality": {
    "storefront": {
      "style": "Soft-premium editorial + bento commerce",
      "materials": ["warm ivory surfaces", "rose-gold metallic accents", "subtle grain/noise", "soft shadows"],
      "layout_principles": [
        "Bento grids for categories + featured products",
        "Editorial typography (serif display) paired with clean sans body",
        "High whitespace, calm rhythm, strong product imagery"
      ]
    },
    "admin": {
      "style": "Clean command center",
      "materials": ["cooler neutrals", "crisp borders", "dense-but-readable tables", "data ink first"],
      "layout_principles": [
        "Left sidebar + top utility bar",
        "Cards for KPIs, tables for operations",
        "Charts with muted palette + clear labels"
      ]
    },
    "ai_admin_chat": {
      "style": "Magical but professional (no neon, no purple)",
      "materials": ["soft teal glow", "champagne highlight", "glass-lite panels (opaque, not transparent)", "typing shimmer"],
      "layout_principles": [
        "3-column on desktop: history sidebar + chat + context/results",
        "On mobile: tabs/Drawer for history and context",
        "Result cards inline in conversation (like tool outputs)"
      ]
    }
  },

  "typography": {
    "google_fonts": {
      "display": {
        "family": "Gloock",
        "fallback": "serif",
        "weights": [400]
      },
      "body": {
        "family": "Manrope",
        "fallback": "ui-sans-serif, system-ui",
        "weights": [400, 500, 600, 700]
      }
    },
    "usage": {
      "h1": "Gloock (tracking-tight)",
      "h2_h3": "Manrope 600/700",
      "body": "Manrope 400/500",
      "numbers_kpi": "Manrope 700 with tabular-nums"
    },
    "scale_tailwind": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "section_title": "text-2xl sm:text-3xl",
      "card_title": "text-base sm:text-lg",
      "body": "text-sm sm:text-base",
      "small": "text-xs"
    },
    "line_height": {
      "display": "leading-[1.05]",
      "body": "leading-6"
    }
  },

  "color_system": {
    "notes": "Warm storefront neutrals + rose-gold accent; admin uses cooler neutrals; AI chat uses teal/champagne glow. No purple gradients.",
    "palette_hex": {
      "ivory": "#FBF7F2",
      "paper": "#FFFDFB",
      "sand": "#F1E7DD",
      "taupe": "#CBB8A7",
      "ink": "#1B1A18",
      "charcoal": "#2A2724",
      "muted_text": "#6B625B",

      "rose_gold": "#C58B7A",
      "rose_gold_deep": "#A86B5B",
      "champagne": "#F3E2C7",

      "teal": "#2F7E7A",
      "teal_soft": "#D7F0EE",

      "success": "#1F7A4D",
      "warning": "#B7791F",
      "danger": "#B42318",

      "border": "#E7D9CE",
      "shadow": "rgba(27, 26, 24, 0.10)"
    },
    "semantic_tokens_hsl_for_shadcn": {
      "background": "30 43% 97%",
      "foreground": "30 10% 10%",
      "card": "30 60% 99%",
      "card-foreground": "30 10% 10%",
      "popover": "30 60% 99%",
      "popover-foreground": "30 10% 10%",

      "primary": "14 33% 62%",
      "primary-foreground": "30 60% 99%",

      "secondary": "28 35% 92%",
      "secondary-foreground": "30 10% 12%",

      "muted": "28 30% 93%",
      "muted-foreground": "25 10% 40%",

      "accent": "174 35% 92%",
      "accent-foreground": "30 10% 12%",

      "destructive": "6 72% 45%",
      "destructive-foreground": "30 60% 99%",

      "border": "22 28% 86%",
      "input": "22 28% 86%",
      "ring": "14 33% 62%",

      "chart-1": "14 33% 62%",
      "chart-2": "174 45% 35%",
      "chart-3": "28 35% 55%",
      "chart-4": "40 65% 55%",
      "chart-5": "6 72% 45%",
      "radius": "0.9rem"
    },
    "gradients_allowed_light": {
      "hero_wash": "linear-gradient(135deg, rgba(243,226,199,0.55) 0%, rgba(215,240,238,0.45) 55%, rgba(251,247,242,0.0) 100%)",
      "cta_soft": "linear-gradient(135deg, #C58B7A 0%, #F3E2C7 100%)",
      "ai_glow": "radial-gradient(600px circle at 20% 0%, rgba(47,126,122,0.18), transparent 55%), radial-gradient(600px circle at 80% 10%, rgba(197,139,122,0.14), transparent 55%)"
    }
  },

  "design_tokens_css": {
    "instructions": "Add these to /app/frontend/src/index.css under :root (keep shadcn tokens; extend with --gs-*). Avoid transition: all.",
    "css": ":root {\n  --gs-bg: #FBF7F2;\n  --gs-surface: #FFFDFB;\n  --gs-surface-2: #F1E7DD;\n  --gs-border: #E7D9CE;\n  --gs-ink: #1B1A18;\n  --gs-muted: #6B625B;\n\n  --gs-primary: #C58B7A;\n  --gs-primary-2: #A86B5B;\n  --gs-champagne: #F3E2C7;\n  --gs-teal: #2F7E7A;\n  --gs-teal-soft: #D7F0EE;\n\n  --gs-radius-sm: 12px;\n  --gs-radius-md: 16px;\n  --gs-radius-lg: 22px;\n\n  --gs-shadow-sm: 0 1px 2px rgba(27,26,24,0.06);\n  --gs-shadow-md: 0 10px 30px rgba(27,26,24,0.10);\n  --gs-shadow-lg: 0 18px 60px rgba(27,26,24,0.14);\n\n  --gs-focus: 0 0 0 4px rgba(197,139,122,0.22);\n\n  --gs-container: 1120px;\n  --gs-gutter: 16px;\n}\n\n::selection { background: rgba(197,139,122,0.25); }\n\nbody { background: var(--gs-bg); }\n\n.gs-noise::before {\n  content: \"\";\n  position: absolute;\n  inset: 0;\n  pointer-events: none;\n  opacity: 0.06;\n  mix-blend-mode: multiply;\n  background-image: url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"160\" height=\"160\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"3\" stitchTiles=\"stitch\"/></filter><rect width=\"160\" height=\"160\" filter=\"url(%23n)\" opacity=\"0.35\"/></svg>');\n}\n"
  },

  "layout_grid": {
    "container": "max-w-[var(--gs-container)] mx-auto px-4 sm:px-6",
    "section_spacing": "py-10 sm:py-14 lg:py-18",
    "bento_grid": {
      "mobile": "grid grid-cols-2 gap-3",
      "desktop": "md:grid-cols-4 md:gap-5",
      "featured_tiles": "Use col-span-2 row-span-2 for 1–2 hero tiles; keep text minimal on tiles."
    },
    "admin_shell": {
      "desktop": "grid grid-cols-[260px_1fr] min-h-screen",
      "mobile": "Sidebar becomes Sheet/Drawer; top bar stays sticky"
    }
  },

  "component_path": {
    "shadcn_primary": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "input": "/app/frontend/src/components/ui/input.jsx",
      "textarea": "/app/frontend/src/components/ui/textarea.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "checkbox": "/app/frontend/src/components/ui/checkbox.jsx",
      "radio_group": "/app/frontend/src/components/ui/radio-group.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "pagination": "/app/frontend/src/components/ui/pagination.jsx",
      "sheet_drawer": "/app/frontend/src/components/ui/sheet.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "alert_dialog": "/app/frontend/src/components/ui/alert-dialog.jsx",
      "dropdown_menu": "/app/frontend/src/components/ui/dropdown-menu.jsx",
      "navigation_menu": "/app/frontend/src/components/ui/navigation-menu.jsx",
      "breadcrumb": "/app/frontend/src/components/ui/breadcrumb.jsx",
      "carousel": "/app/frontend/src/components/ui/carousel.jsx",
      "scroll_area": "/app/frontend/src/components/ui/scroll-area.jsx",
      "separator": "/app/frontend/src/components/ui/separator.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx",
      "sonner_toast": "/app/frontend/src/components/ui/sonner.jsx",
      "calendar": "/app/frontend/src/components/ui/calendar.jsx",
      "command": "/app/frontend/src/components/ui/command.jsx",
      "tooltip": "/app/frontend/src/components/ui/tooltip.jsx",
      "avatar": "/app/frontend/src/components/ui/avatar.jsx"
    },
    "recommended_additions": {
      "framer_motion": {
        "why": "Micro-interactions, page transitions, chat streaming feel",
        "install": "npm i framer-motion",
        "usage": "Use motion.div for card hover lift and chat message entrance."
      },
      "recharts": {
        "why": "Admin KPI charts",
        "install": "npm i recharts",
        "usage": "AreaChart for revenue, BarChart for orders, Pie for category mix."
      },
      "lucide_react": {
        "why": "Consistent icons (no emoji)",
        "install": "npm i lucide-react",
        "usage": "Use icons in buttons, nav, stat cards."
      }
    }
  },

  "components_and_patterns": {
    "buttons": {
      "shape": "Premium / Elegant: rounded-xl (10–14px), tall touch targets",
      "sizes": {
        "sm": "h-9 px-3 text-sm",
        "md": "h-11 px-5 text-sm",
        "lg": "h-12 px-6 text-base"
      },
      "variants": {
        "primary": {
          "classes": "bg-[color:var(--gs-primary)] text-white shadow-[var(--gs-shadow-sm)] hover:bg-[color:var(--gs-primary-2)] focus-visible:outline-none focus-visible:ring-0 focus-visible:shadow-[var(--gs-focus)]",
          "motion": "transition-colors duration-200; active:scale-[0.98]"
        },
        "secondary": {
          "classes": "bg-[color:var(--gs-surface)] text-[color:var(--gs-ink)] border border-[color:var(--gs-border)] hover:bg-[color:var(--gs-surface-2)]",
          "motion": "transition-colors duration-200; active:scale-[0.98]"
        },
        "ghost": {
          "classes": "bg-transparent text-[color:var(--gs-ink)] hover:bg-[rgba(197,139,122,0.10)]",
          "motion": "transition-colors duration-200"
        }
      },
      "data_testid_examples": [
        "data-testid=\"hero-primary-cta-button\"",
        "data-testid=\"product-card-add-to-cart-button\"",
        "data-testid=\"admin-ai-chat-send-button\""
      ]
    },

    "cards": {
      "base": "rounded-[var(--gs-radius-md)] bg-[color:var(--gs-surface)] border border-[color:var(--gs-border)] shadow-[var(--gs-shadow-sm)]",
      "hover": "hover:shadow-[var(--gs-shadow-md)] hover:-translate-y-0.5 transition-shadow duration-200",
      "product_card": {
        "layout": "Image (aspect-square) + title + price + quick actions",
        "quick_actions": "On desktop hover: show Add to cart + Wishlist; on mobile always visible",
        "badges": "Use Badge for ‘New’, ‘Bestseller’, ‘Digital’"
      },
      "stat_card": {
        "layout": "Icon + label + big number + delta chip",
        "classes": "p-4 sm:p-5"
      }
    },

    "inputs": {
      "base": "h-11 rounded-xl bg-white border-[color:var(--gs-border)] focus-visible:ring-0 focus-visible:shadow-[var(--gs-focus)]",
      "search": "Add left icon + clear button; show suggestions in Command component",
      "data_testid_examples": [
        "data-testid=\"global-search-input\"",
        "data-testid=\"login-email-input\"",
        "data-testid=\"checkout-phone-input\""
      ]
    },

    "navigation": {
      "storefront_header": {
        "structure": "Top bar: logo + search + account + cart. Secondary row: category pills (scrollable on mobile).",
        "components": ["navigation-menu", "input", "sheet"],
        "mobile": "Use Sheet for menu; keep cart icon always visible."
      },
      "admin_sidebar": {
        "structure": "Logo + primary nav + quick actions + user avatar",
        "components": ["scroll-area", "separator", "tooltip"],
        "active_state": "Left border accent in rose-gold + subtle background tint"
      }
    },

    "tables": {
      "admin_tables": {
        "components": ["table", "dropdown-menu", "pagination"],
        "row_density": "Comfortable: py-3; keep sticky header on desktop",
        "actions": "Row kebab menu (DropdownMenu) for Edit, Duplicate, Archive",
        "empty_state": "Card with CTA button + short hint"
      }
    },

    "filters": {
      "shop_filters": {
        "desktop": "Left filter column (sticky) with Accordion sections",
        "mobile": "Filters open in Sheet from bottom/right",
        "components": ["accordion", "checkbox", "slider", "select"],
        "data_testid_examples": [
          "data-testid=\"shop-filters-open-button\"",
          "data-testid=\"filter-price-slider\"",
          "data-testid=\"filter-category-checkbox-jewellery\""
        ]
      }
    }
  },

  "page_blueprints": {
    "home": {
      "hero": {
        "layout": "Split hero: left editorial copy + CTAs; right bento collage (2–3 tiles) with category highlights.",
        "background": "Use hero_wash gradient only in top 15–20% + noise overlay wrapper.",
        "ctas": ["Shop Women", "Explore Digital Tools"],
        "micro_interactions": [
          "CTA hover: subtle color shift + shadow",
          "Bento tiles: hover lift + image zoom (scale 1.03)"
        ],
        "data_testid": {
          "primary_cta": "hero-primary-cta-button",
          "secondary_cta": "hero-secondary-cta-button"
        }
      },
      "categories_grid": {
        "layout": "Bento grid 2 cols mobile / 4 cols desktop; 1 featured tile (col-span-2) for ‘Digital Products’.",
        "cards": "CategoryCard: image + label + item count",
        "data_testid": "home-categories-grid"
      },
      "trending_products": {
        "layout": "Carousel on mobile, 4-up grid on desktop",
        "components": ["carousel", "card", "badge", "button"],
        "data_testid": "home-trending-products"
      },
      "testimonials": {
        "layout": "3 cards, editorial quotes, avatar + location",
        "note": "No gradients behind long text; keep solid surface.",
        "data_testid": "home-testimonials"
      },
      "newsletter": {
        "layout": "Compact CTA band with champagne background + input",
        "data_testid": "newsletter-signup-form"
      }
    },

    "shop": {
      "layout": "Header with results count + sort Select; grid products; filters as described.",
      "product_grid": "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-5",
      "data_testid": {
        "sort_select": "shop-sort-select",
        "product_grid": "shop-product-grid"
      }
    },

    "product_detail": {
      "layout": "Mobile: stacked gallery then details; Desktop: 2-col (gallery left, details right).",
      "gallery": "Use Carousel + thumbnails; keep background paper.",
      "cta": "Sticky Add-to-cart bar on mobile (bottom).",
      "components": ["carousel", "tabs", "badge", "button"],
      "data_testid": {
        "add_to_cart": "product-detail-add-to-cart-button",
        "quantity": "product-detail-quantity-input"
      }
    },

    "cart_checkout": {
      "cart": "Line items with image, qty stepper, remove; order summary card sticky on desktop.",
      "checkout": "2-step feel: Shipping details + Review (Tabs). Payment UI placeholder.",
      "components": ["tabs", "card", "input", "select", "separator"],
      "data_testid": {
        "checkout_submit": "checkout-place-order-button"
      }
    },

    "auth": {
      "layout": "Centered card but page content left-aligned inside card; add trust bullets (returns, secure).",
      "components": ["card", "input", "button", "separator"],
      "data_testid": {
        "login_submit": "login-form-submit-button",
        "signup_submit": "signup-form-submit-button"
      }
    },

    "account": {
      "layout": "Tabs: Profile, Orders, Addresses",
      "orders": "Table on desktop, cards on mobile",
      "data_testid": "account-tabs"
    },

    "admin_dashboard": {
      "layout": "Sidebar + top bar; main: KPI row + charts + recent orders table",
      "kpis": ["Revenue", "Orders", "Customers", "Low stock"],
      "charts": "Recharts: AreaChart revenue, BarChart orders",
      "data_testid": {
        "kpi_revenue": "admin-kpi-revenue",
        "recent_orders": "admin-recent-orders-table"
      }
    },

    "admin_crud_pages": {
      "products": "Table + ‘Add product’ Dialog; bulk actions toolbar",
      "orders": "Table + status chips + Drawer for order detail",
      "suppliers": "Table + supplier profile panel",
      "customers": "Table + segmentation badges",
      "data_testid": {
        "add_product": "admin-add-product-button",
        "orders_filter": "admin-orders-status-filter"
      }
    },

    "admin_ai_chat": {
      "layout": {
        "desktop": "grid grid-cols-[280px_1fr_360px] gap-4",
        "mobile": "History + Context open via Sheet; chat full width"
      },
      "left_sidebar_history": {
        "content": "Command history, saved prompts, quick actions",
        "components": ["scroll-area", "button", "separator"],
        "data_testid": "admin-ai-chat-history"
      },
      "chat_center": {
        "message_bubbles": {
          "admin": "bg-white border border-[color:var(--gs-border)]",
          "assistant": "bg-[color:var(--gs-teal-soft)] border border-[rgba(47,126,122,0.25)]"
        },
        "composer": "Sticky bottom composer with Textarea + Send button + suggestion chips",
        "components": ["textarea", "button", "badge", "card"],
        "data_testid": {
          "composer": "admin-ai-chat-composer",
          "input": "admin-ai-chat-input",
          "send": "admin-ai-chat-send-button"
        }
      },
      "right_context_panel": {
        "content": "Live results: tool cards (Product created, Order updated), JSON preview collapsible, ‘Undo’ actions",
        "components": ["tabs", "card", "collapsible", "badge"],
        "data_testid": "admin-ai-chat-context-panel"
      },
      "magic_microinteractions": [
        "Streaming indicator: 3-dot shimmer (no emoji)",
        "Result cards slide-in from bottom with slight blur",
        "Suggestion chips animate in on empty chat",
        "Command success toast via Sonner"
      ]
    }
  },

  "motion": {
    "principles": [
      "Use motion to clarify state changes (added to cart, filters applied, AI executed).",
      "Prefer opacity/translate/scale micro-motions; keep durations 160–240ms.",
      "Respect prefers-reduced-motion."
    ],
    "framer_motion_snippets_js": {
      "card_hover": "import { motion } from 'framer-motion';\n\nexport const HoverCard = ({ children }) => (\n  <motion.div\n    whileHover={{ y: -2 }}\n    whileTap={{ scale: 0.98 }}\n    transition={{ duration: 0.18 }}\n  >\n    {children}\n  </motion.div>\n);",
      "chat_message_enter": "<motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>...</motion.div>"
    }
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast: ink on ivory; avoid low-contrast taupe text.",
      "Visible focus: use shadow ring (--gs-focus) on inputs/buttons.",
      "Touch targets: min 44px height for primary actions.",
      "Use aria-label for icon-only buttons (cart, wishlist, send).",
      "Prefer reduced motion support for animations."
    ]
  },

  "image_urls": {
    "hero_and_editorial": [
      {
        "category": "home-hero-right-tile",
        "description": "Minimal home decor neutral scene (works as bento tile background)",
        "url": "https://images.unsplash.com/photo-1598082862596-821983eb115e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwxfHxtaW5pbWFsJTIwaG9tZSUyMGRlY29yJTIwbmV1dHJhbCUyMG1vZGVybiUyMGludGVyaW9yfGVufDB8fHx0ZWFsfDE3ODI1NzY4MjR8MA&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "ai-learning-hero",
        "description": "Woman working on laptop (blurred face acceptable; use as empowerment visual)",
        "url": "https://images.unsplash.com/photo-1617128610245-c348bcc22d36?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHVzaW5nJTIwbGFwdG9wJTIwbW9kZXJuJTIwZGVzayUyMHNvZnQlMjBsaWdodHxlbnwwfHx8dGVhbHwxNzgyNTc2ODQwfDA&ixlib=rb-4.1.0&q=85"
      }
    ],
    "kids_category": [
      {
        "category": "category-kids",
        "description": "Kids toys flat lay (clean, bright)",
        "url": "https://images.unsplash.com/photo-1613536491198-a0afa1916b3b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwxfHxraWRzJTIwdG95cyUyMGZsYXQlMjBsYXklMjBuZXV0cmFsJTIwYmFja2dyb3VuZCUyMG1pbmltYWx8ZW58MHx8fHdoaXRlfDE3ODI1NzY4NDR8MA&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "category-kids-pattern",
        "description": "Playful pattern tile for kids section (use sparingly)",
        "url": "https://images.unsplash.com/photo-1631935091182-a7795017ce5f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwzfHxraWRzJTIwdG95cyUyMGZsYXQlMjBsYXklMjBuZXV0cmFsJTIwYmFja2dyb3VuZCUyMG1pbmltYWx8ZW58MHx8fHdoaXRlfDE3ODI1NzY4NDR8MA&ixlib=rb-4.1.0&q=85"
      }
    ]
  },

  "instructions_to_main_agent": {
    "global": [
      "Remove default CRA App.css centered header usage; do not center the whole app container.",
      "Update /app/frontend/src/index.css :root shadcn HSL tokens to match semantic_tokens_hsl_for_shadcn; then add --gs-* tokens.",
      "Use Manrope for body and Gloock for hero headings via Google Fonts import in index.html or CSS.",
      "All interactive + key informational elements MUST include data-testid (kebab-case).",
      "No emoji icons; use lucide-react.",
      "No transparent backgrounds with dark text; keep surfaces opaque (paper/white)."
    ],
    "storefront_build_order": [
      "Header (logo/search/cart/account) + category pills",
      "Home hero with bento collage",
      "Category bento grid",
      "Product card system + shop filters",
      "PDP gallery + sticky mobile CTA",
      "Cart + checkout UI",
      "Auth + account tabs"
    ],
    "admin_build_order": [
      "Admin shell (sidebar + top bar)",
      "Dashboard KPIs + charts + recent orders",
      "CRUD tables with dialogs/drawers",
      "AI Chat page (history sidebar + chat + context panel)"
    ],
    "ai_chat_execution_ui": [
      "Represent AI actions as ‘tool cards’ with status: running/success/error.",
      "Use Sonner toasts for success/error (e.g., ‘Product created’).",
      "Include ‘Undo’ button on result cards where possible (UI only if backend not ready)."
    ]
  },

  "appendix_general_ui_ux_design_guidelines": "- You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n- You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n- NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals."
}
