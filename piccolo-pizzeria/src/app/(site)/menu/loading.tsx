import { Skeleton } from "@/components/ui/skeleton";

export default function MenuLoading() {
  return (
    <div>
      <div className="border-b border-cream-100/10 bg-char-900">
        <div className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
          <Skeleton className="h-4 w-24 bg-cream-50/10" />
          <Skeleton className="mt-3 h-10 w-72 bg-cream-50/10" />
        </div>
      </div>
      <div className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-24 rounded-full" />
          ))}
        </div>
        <div className="mt-8 grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="aspect-[4/3] w-full rounded-2xl" />
              <Skeleton className="mt-3 h-6 w-3/4" />
              <Skeleton className="mt-2 h-4 w-1/2" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
