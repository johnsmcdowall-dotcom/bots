"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/types";

export function CategoryNav({ categories }: { categories: Category[] }) {
  const [active, setActive] = useState(categories[0]?.slug);
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sections = categories
      .map((c) => document.getElementById(`category-${c.slug}`))
      .filter((el): el is HTMLElement => Boolean(el));

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) {
          const slug = visible[0].target.id.replace("category-", "");
          setActive(slug);
        }
      },
      { rootMargin: "-140px 0px -60% 0px", threshold: 0 }
    );

    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, [categories]);

  useEffect(() => {
    const btn = navRef.current?.querySelector<HTMLButtonElement>(`[data-slug="${active}"]`);
    btn?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }, [active]);

  function scrollTo(slug: string) {
    const el = document.getElementById(`category-${slug}`);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - 128;
    window.scrollTo({ top: y, behavior: "smooth" });
    setActive(slug);
  }

  return (
    <div className="sticky top-16 z-20 border-b border-char-200/70 bg-cream-100/95 backdrop-blur-md sm:top-20">
      <div
        ref={navRef}
        className="no-scrollbar mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 py-3 sm:px-6 lg:px-8"
      >
        {categories.map((cat) => (
          <button
            key={cat.id}
            data-slug={cat.slug}
            onClick={() => scrollTo(cat.slug)}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
              active === cat.slug ? "bg-char-900 text-cream-50" : "bg-char-900/[0.05] text-char-600 hover:bg-char-900/10"
            )}
          >
            {cat.name}
          </button>
        ))}
      </div>
    </div>
  );
}
