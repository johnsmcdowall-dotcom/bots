import { Skeleton } from "@/components/ui/skeleton";

export default function OrdersLoading() {
  return (
    <div>
      <Skeleton className="h-9 w-40" />
      <div className="mt-6 grid grid-cols-2 gap-4 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i}>
            <Skeleton className="h-4 w-20" />
            <div className="mt-3 space-y-3">
              <Skeleton className="h-28 w-full rounded-2xl" />
              <Skeleton className="h-28 w-full rounded-2xl" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
