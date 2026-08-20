import type { Metadata } from "next";
import { AlertTriangle, Phone } from "lucide-react";
import { getCategories, getProducts } from "@/lib/data/menu";
import { getBusinessSettings } from "@/lib/data/business";
import { ALLERGEN_LIBRARY } from "@/lib/types";

export const metadata: Metadata = {
  title: "Allergen Information",
  description: "Allergen information for the Piccolo Pizzeria menu.",
};

export default async function AllergensPage() {
  const [categories, products, business] = await Promise.all([getCategories(), getProducts(), getBusinessSettings()]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <p className="text-xs font-semibold uppercase tracking-widest text-fire-600">Important</p>
      <h1 className="mt-2 font-display text-4xl font-semibold text-char-900 sm:text-5xl">Allergen Information</h1>

      <div className="mt-6 flex items-start gap-3 rounded-2xl bg-fire-500/10 p-5 text-fire-700">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="text-sm leading-relaxed">
          <p>
            All our food is prepared in a small trailer kitchen that handles gluten, dairy, nuts
            and other allergens. While we take care with ingredients and preparation, we{" "}
            <strong>cannot guarantee any dish is completely free from traces of any allergen</strong>{" "}
            due to the working environment.
          </p>
          <p className="mt-2">
            If you have a food allergy or intolerance, please{" "}
            <a href={`tel:${business.phone.replace(/\s+/g, "")}`} className="inline-flex items-center gap-1 font-semibold underline">
              <Phone className="h-3.5 w-3.5" /> call us on {business.phone}
            </a>{" "}
            before ordering so we can talk it through with you.
          </p>
        </div>
      </div>

      {categories.map((category) => {
        const items = products.filter((p) => p.categoryId === category.id);
        if (items.length === 0) return null;

        return (
          <section key={category.id} className="mt-10">
            <h2 className="font-display text-2xl font-semibold text-char-900">{category.name}</h2>
            <div className="mt-4 overflow-x-auto rounded-2xl border border-char-200">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="bg-cream-200/60 text-xs font-semibold uppercase tracking-wide text-char-500">
                  <tr>
                    <th className="px-4 py-3">Item</th>
                    <th className="px-4 py-3">Contains</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-char-200">
                  {items.map((product) => (
                    <tr key={product.id}>
                      <td className="px-4 py-3 font-medium text-char-800">{product.name}</td>
                      <td className="px-4 py-3 text-char-500">
                        {product.allergens.length === 0
                          ? "—"
                          : product.allergens
                              .map((code) => ALLERGEN_LIBRARY.find((a) => a.code === code)?.label ?? code)
                              .join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </div>
  );
}
