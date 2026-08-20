import { OpeningHoursEditor } from "@/components/admin/OpeningHoursEditor";
import { getSpecialHours, getWeeklyHours } from "@/lib/data/business";

export default async function AdminOpeningHoursPage() {
  const [weeklyHours, specialHours] = await Promise.all([getWeeklyHours(), getSpecialHours()]);

  return (
    <div>
      <h1 className="font-display text-3xl text-char-900">Opening Hours</h1>
      <p className="mt-1 text-char-500">Changes apply immediately to the opening status shown to customers.</p>
      <div className="mt-6 max-w-3xl">
        <OpeningHoursEditor weeklyHours={weeklyHours} specialHours={specialHours} />
      </div>
    </div>
  );
}
