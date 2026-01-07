import { Suspense } from "react";
import { getStartups, getStats, getIndustries } from "@/lib/data";
import { StatsCards } from "@/components/StatsCards";
import { Filters } from "@/components/Filters";
import { StartupGrid } from "@/components/StartupGrid";

interface PageProps {
  searchParams: Promise<{
    search?: string;
    industry?: string;
    deal?: string;
  }>;
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const [startups, stats, industries] = await Promise.all([
    getStartups(),
    getStats(),
    getIndustries(),
  ]);

  // Apply filters
  let filteredStartups = startups;

  if (params.search) {
    const search = params.search.toLowerCase();
    filteredStartups = filteredStartups.filter(
      (s) =>
        s.name.toLowerCase().includes(search) ||
        s.name_ar?.includes(params.search!) ||
        s.description.toLowerCase().includes(search)
    );
  }

  if (params.industry) {
    filteredStartups = filteredStartups.filter(
      (s) => s.industry === params.industry
    );
  }

  if (params.deal !== undefined && params.deal !== "") {
    const dealMade = params.deal === "true";
    filteredStartups = filteredStartups.filter((s) => s.deal_made === dealMade);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Shark Tank Egypt Dashboard
          </h1>
          <p className="mt-1 text-gray-500">
            Browse all startups from Shark Tank Egypt episodes
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <StatsCards stats={stats} />

        <Suspense fallback={<div>Loading filters...</div>}>
          <Filters industries={industries} />
        </Suspense>

        <div className="mb-4 text-sm text-gray-500">
          Showing {filteredStartups.length} of {startups.length} startups
        </div>

        <StartupGrid startups={filteredStartups} />
      </main>

      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
          Data collected from Shark Tank Egypt YouTube episodes
        </div>
      </footer>
    </div>
  );
}
