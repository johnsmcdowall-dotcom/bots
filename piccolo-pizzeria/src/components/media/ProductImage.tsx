import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * Resolves a product's `imageUrl` to a real asset. Products seeded without
 * real photography use the `placeholder:<category>:<variant>` convention,
 * which maps to a hand-drawn SVG in /public/images/placeholders — swap a
 * product's `imageUrl` for a real photo path (or Supabase Storage URL) at
 * any time and this keeps working unchanged.
 */
function resolveSrc(imageUrl: string): string {
  if (imageUrl.startsWith("placeholder:")) {
    const [, category, variant] = imageUrl.split(":");
    return `/images/placeholders/${category}-${variant}.svg`;
  }
  return imageUrl || "/images/placeholders/pizzas-0.svg";
}

export function ProductImage({
  imageUrl,
  alt,
  className,
  sizes = "(min-width: 768px) 33vw, 100vw",
  priority = false,
}: {
  imageUrl: string;
  alt: string;
  className?: string;
  sizes?: string;
  priority?: boolean;
}) {
  const src = resolveSrc(imageUrl);
  const isSvg = src.endsWith(".svg");
  return (
    <Image
      src={src}
      alt={alt}
      fill
      unoptimized={isSvg}
      sizes={sizes}
      priority={priority}
      className={cn("object-cover", className)}
    />
  );
}
