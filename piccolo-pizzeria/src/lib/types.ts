// Core domain types shared between the seed-data fallback and the Supabase-backed
// data layer. Money is always stored/passed as integer minor units (pence).

export type OrderMethod = "collection" | "delivery";
export type OrderTiming = "asap" | "scheduled";

export type DietaryTag = "vegetarian" | "vegan" | "spicy" | "gluten_free";

export interface Allergen {
  code: string;
  label: string;
}

export const ALLERGEN_LIBRARY: Allergen[] = [
  { code: "gluten", label: "Gluten" },
  { code: "dairy", label: "Dairy" },
  { code: "eggs", label: "Eggs" },
  { code: "fish", label: "Fish" },
  { code: "crustaceans", label: "Crustaceans" },
  { code: "nuts", label: "Tree nuts" },
  { code: "peanuts", label: "Peanuts" },
  { code: "soya", label: "Soya" },
  { code: "celery", label: "Celery" },
  { code: "mustard", label: "Mustard" },
  { code: "sulphites", label: "Sulphites" },
];

export interface Category {
  id: string;
  slug: string;
  name: string;
  description?: string;
  sortOrder: number;
}

export interface ModifierOption {
  id: string;
  name: string;
  priceMinor: number; // additional price in pence, can be 0
  soldOut?: boolean;
  isDefault?: boolean;
}

export interface ModifierGroup {
  id: string;
  name: string;
  description?: string;
  required: boolean;
  minSelect: number;
  maxSelect: number; // 1 = single-select, >1 = multi-select
  options: ModifierOption[];
}

export interface Product {
  id: string;
  categoryId: string;
  slug: string;
  name: string;
  description: string;
  priceMinor: number;
  imageUrl: string;
  dietary: DietaryTag[];
  allergens: string[]; // allergen codes
  soldOut: boolean;
  featured: boolean;
  popular: boolean;
  isNew: boolean;
  sortOrder: number;
  modifierGroupIds: string[];
  /** Optional limited-quantity tracking — most products leave this false and are unlimited. */
  stockLimited: boolean;
  /** Only meaningful when stockLimited is true. */
  stockRemaining: number | null;
}

export interface DayHours {
  isOpen: boolean;
  openTime: string; // "HH:mm"
  closeTime: string; // "HH:mm"
}

/** 0 = Sunday ... 6 = Saturday, matching Date#getDay() */
export type WeeklyHours = Record<number, DayHours>;

export interface SpecialHours {
  id: string;
  date: string; // "YYYY-MM-DD"
  label: string;
  isOpen: boolean;
  openTime?: string;
  closeTime?: string;
}

export interface DeliveryZone {
  id: string;
  postcodePrefixes: string[]; // e.g. ["TS18", "TS17"]
  feeMinor: number;
  minOrderMinor: number;
  freeDeliveryThresholdMinor?: number;
  estimatedMinutes: number;
}

export interface BusinessSettings {
  name: string;
  tagline: string;
  phone: string;
  email: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  postcode: string;
  latitude: number;
  longitude: number;
  instagramUrl?: string;
  facebookUrl?: string;
  tiktokUrl?: string;
  orderingPaused: boolean;
  orderingPausedMessage?: string;
  asapOrdersEnabled: boolean;
  scheduledOrdersEnabled: boolean;
  deliveryEnabled: boolean;
  currentWaitMinutes: number;
  minPrepMinutes: number;
  maxAdvanceOrderDays: number;
  slotIntervalMinutes: number;
  ordersPerSlot: number;
  deliveryOrdersPerSlot: number;
}

export interface TimeSlot {
  time: string; // "HH:mm"
  dateISO: string; // "YYYY-MM-DD"
  available: boolean;
  remaining: number;
  label: "available" | "nearly-full" | "unavailable";
}

export interface OpeningStatus {
  isOpen: boolean;
  reason?: "closed_day" | "outside_hours" | "special_closure" | "manual_pause";
  message: string;
  nextOpenLabel?: string;
  todayHours?: DayHours;
}

export interface PromoCode {
  id: string;
  code: string;
  type: "percentage" | "fixed";
  value: number; // percent (1-100) or minor units
  minBasketMinor: number;
  startsAt?: string;
  endsAt?: string;
  usageLimit?: number;
  timesUsed: number;
  active: boolean;
}

export type OrderStatus =
  | "pending_payment"
  | "received"
  | "accepted"
  | "preparing"
  | "ready"
  | "completed"
  | "cancelled";

export interface CartModifierSelection {
  groupId: string;
  groupName: string;
  optionIds: string[];
}

export interface CartLine {
  lineId: string;
  productId: string;
  name: string;
  imageUrl: string;
  basePriceMinor: number;
  quantity: number;
  modifiers: {
    groupId: string;
    groupName: string;
    optionId: string;
    optionName: string;
    priceMinor: number;
  }[];
  notes?: string;
}

export interface OrderItemRecord {
  productId: string;
  name: string;
  unitPriceMinor: number;
  quantity: number;
  lineTotalMinor: number;
  notes?: string;
  modifiers: {
    groupId: string;
    optionId: string;
    groupName: string;
    optionName: string;
    priceMinor: number;
  }[];
}

export interface OrderRecord {
  id: string;
  orderNumber: string;
  status: OrderStatus;
  method: OrderMethod;
  timing: OrderTiming;
  requestedTime: string; // ISO datetime the order is scheduled/estimated for
  createdAt: string;
  customer: {
    firstName: string;
    lastName: string;
    phone: string;
    email: string;
  };
  address?: {
    line1: string;
    line2?: string;
    postcode: string;
  };
  notes?: string;
  items: OrderItemRecord[];
  subtotalMinor: number;
  deliveryFeeMinor: number;
  discountMinor: number;
  totalMinor: number;
  promoCode?: string;
  paymentStatus: "pending" | "paid" | "failed";
  stripePaymentIntentId?: string;
}
