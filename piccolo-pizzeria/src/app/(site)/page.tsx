import { Hero } from "@/components/home/Hero";
import { ReorderBanner } from "@/components/home/ReorderBanner";
import { FeaturedMenu } from "@/components/home/FeaturedMenu";
import { FoodMoment } from "@/components/home/FoodMoment";
import { StoryTeaser } from "@/components/home/StoryTeaser";
import { FindUsTeaser } from "@/components/home/FindUsTeaser";
import { InstagramGallery } from "@/components/home/InstagramGallery";
import { getBusinessSettings, getSpecialHours, getWeeklyHours } from "@/lib/data/business";
import { getProducts } from "@/lib/data/menu";
import { restaurantJsonLd } from "@/lib/seo";

export default async function HomePage() {
  const [business, weeklyHours, specialHours, products] = await Promise.all([
    getBusinessSettings(),
    getWeeklyHours(),
    getSpecialHours(),
    getProducts(),
  ]);

  const jsonLd = restaurantJsonLd(business, weeklyHours);

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Hero business={business} weeklyHours={weeklyHours} specialHours={specialHours} />
      <ReorderBanner />
      <FeaturedMenu products={products} />
      <FoodMoment />
      <StoryTeaser />
      <FindUsTeaser business={business} weeklyHours={weeklyHours} />
      <InstagramGallery business={business} />
    </>
  );
}
