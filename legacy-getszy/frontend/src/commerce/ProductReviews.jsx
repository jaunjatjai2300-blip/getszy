/**
 * Product reviews — real proof only.
 *
 * The backend has had a complete review pipeline for a while (submit, admin
 * moderation, approved-only public read, avg_rating written back onto the
 * product) but NO frontend consumed it — so customers could not submit a review
 * at all, and proof could never accumulate. This closes that loop.
 *
 * Honesty rules:
 *   - reads GET /reviews/product/{id}, which returns APPROVED reviews only
 *   - when there are none, the summary is not rendered at all: no "0 reviews",
 *     no empty stars, no placeholder testimonial
 *   - nothing is fabricated, averaged optimistically, or seeded
 *   - a submitted review is explicitly described as pending moderation, because
 *     that is what the backend actually does
 */
import { useCallback, useEffect, useState } from "react";
import { Star } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function Stars({ value, size = "h-4 w-4" }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={size}
          style={{
            fill: n <= Math.round(value) ? "var(--gs-primary)" : "transparent",
            color: "var(--gs-primary)",
          }}
        />
      ))}
    </span>
  );
}

function RatingInput({ value, onChange }) {
  return (
    <div role="radiogroup" aria-label="Your rating" className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
          onClick={() => onChange(n)}
          data-testid={`review-star-${n}`}
          className="grid h-11 w-11 place-items-center rounded-full transition-colors"
        >
          <Star
            className="h-6 w-6"
            style={{
              fill: n <= value ? "var(--gs-primary)" : "transparent",
              color: "var(--gs-primary)",
            }}
          />
        </button>
      ))}
    </div>
  );
}

export default function ProductReviews({ productId, productName }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const load = useCallback(() => {
    if (!productId) return;
    api
      .get(`/reviews/product/${productId}`)
      .then(({ data: d }) => setData(d))
      .catch(() => setData(null));
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!rating) { toast.error("Please choose a rating first"); return; }
    setBusy(true);
    try {
      await api.post("/reviews", { product_id: productId, rating, comment, title });
      setSubmitted(true);
      setRating(0); setTitle(""); setComment("");
      // Approved reviews only appear after moderation, so do not optimistically
      // insert this one into the list — that would show the customer a review
      // the public cannot yet see.
      toast.success("Thank you — your review is with our team for approval.");
    } catch (err) {
      const msg = err?.response?.data?.detail;
      toast.error(typeof msg === "string" ? msg : "Could not submit your review");
    } finally {
      setBusy(false);
    }
  };

  const count = data?.count || 0;
  const average = data?.average_rating || 0;
  const items = data?.items || [];

  return (
    <section className="gs-container gs-section !pt-0" data-testid="product-reviews">
      <div className="mx-auto max-w-3xl">
        <h2 className="gs-h2 font-display" style={{ color: "var(--gs-ink)" }}>
          Reviews
        </h2>

        {/* Summary renders ONLY when real approved reviews exist. No zero-state
            star row, no invented average. */}
        {count > 0 && (
          <div className="mt-4 flex items-center gap-3" data-testid="review-summary">
            <Stars value={average} />
            <span className="text-sm" style={{ color: "var(--gs-muted)" }}>
              {average} · {count} {count === 1 ? "review" : "reviews"}
            </span>
          </div>
        )}

        {count > 0 ? (
          <ul className="mt-8 space-y-6">
            {items.map((r) => (
              <li key={r.id} className="gs-card p-5" data-testid={`review-${r.id}`}>
                <div className="flex items-center gap-3">
                  <Stars value={r.rating} size="h-3.5 w-3.5" />
                  <span className="text-sm font-semibold" style={{ color: "var(--gs-ink)" }}>
                    {r.user_name || "Customer"}
                  </span>
                </div>
                {r.title && (
                  <p className="mt-2 font-semibold" style={{ color: "var(--gs-ink)" }}>{r.title}</p>
                )}
                {r.comment && (
                  <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--gs-muted)" }}>
                    {r.comment}
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm" style={{ color: "var(--gs-muted)" }}>
            No reviews yet. If you have bought this, yours would be the first.
          </p>
        )}

        {/* Write a review */}
        <div className="mt-10">
          {!user ? (
            <p className="text-sm" style={{ color: "var(--gs-muted)" }}>
              <a href="/login" className="font-semibold underline underline-offset-4" style={{ color: "var(--gs-primary-2)" }}>
                Sign in
              </a>{" "}
              to write a review.
            </p>
          ) : submitted ? (
            <p className="text-sm" style={{ color: "var(--gs-muted)" }} data-testid="review-submitted">
              Your review has been sent for approval. It will appear here once our team publishes it.
            </p>
          ) : (
            <form onSubmit={submit} data-testid="review-form">
              <h3 className="gs-h3 font-display" style={{ color: "var(--gs-ink)" }}>
                Write a review
              </h3>
              <p className="mt-1 text-sm" style={{ color: "var(--gs-muted)" }}>
                Reviews are read by our team before they are published.
              </p>

              <div className="mt-4">
                <RatingInput value={rating} onChange={setRating} />
              </div>

              <label className="mt-5 block">
                <span className="text-sm font-semibold" style={{ color: "var(--gs-ink)" }}>Title</span>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={80}
                  data-testid="review-title"
                  placeholder={`What stood out about ${productName || "this"}?`}
                  className="mt-1 w-full rounded-xl border bg-white px-4 py-3 text-sm outline-none"
                  style={{ borderColor: "var(--gs-border)" }}
                />
              </label>

              <label className="mt-4 block">
                <span className="text-sm font-semibold" style={{ color: "var(--gs-ink)" }}>Your review</span>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={4}
                  maxLength={1000}
                  data-testid="review-comment"
                  className="mt-1 w-full rounded-xl border bg-white px-4 py-3 text-sm outline-none"
                  style={{ borderColor: "var(--gs-border)" }}
                />
              </label>

              <button
                type="submit"
                disabled={busy}
                data-testid="review-submit"
                className="mt-5 inline-flex min-h-[44px] items-center justify-center rounded-full px-7 text-sm font-semibold text-white transition-colors disabled:opacity-60"
                style={{ background: "var(--gs-primary)" }}
              >
                {busy ? "Sending…" : "Submit review"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
