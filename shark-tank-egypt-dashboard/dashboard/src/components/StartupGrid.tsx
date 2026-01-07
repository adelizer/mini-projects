import { Startup } from "@/types/startup";
import { StartupCard } from "./StartupCard";

interface StartupGridProps {
  startups: Startup[];
}

export function StartupGrid({ startups }: StartupGridProps) {
  if (startups.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-lg">No startups found.</p>
        <p className="text-gray-400 text-sm mt-2">
          Try adjusting your filters or run the scraper to collect data.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {startups.map((startup) => (
        <StartupCard key={startup.id} startup={startup} />
      ))}
    </div>
  );
}
