import { BusinessSettingsEditor } from "@/components/admin/BusinessSettingsEditor";
import { getBusinessSettings } from "@/lib/data/business";

export default async function AdminSettingsPage() {
  const business = await getBusinessSettings();

  return (
    <div>
      <h1 className="font-display text-3xl text-char-900">Settings</h1>
      <p className="mt-1 text-char-500">Control ordering, timing and business details.</p>
      <div className="mt-6 max-w-3xl">
        <BusinessSettingsEditor business={business} />
      </div>
    </div>
  );
}
