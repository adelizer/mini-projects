import { formatCurrency, formatPercentage } from "@/lib/utils";

interface StatsCardsProps {
  stats: {
    totalStartups: number;
    dealsCount: number;
    dealRate: number;
    totalInvestment: number;
    episodesCount: number;
  };
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: "Total Startups",
      value: stats.totalStartups.toString(),
      color: "bg-blue-500",
    },
    {
      title: "Deals Made",
      value: stats.dealsCount.toString(),
      subtitle: formatPercentage(stats.dealRate) + " success rate",
      color: "bg-green-500",
    },
    {
      title: "Total Investment",
      value: formatCurrency(stats.totalInvestment),
      color: "bg-purple-500",
    },
    {
      title: "Episodes",
      value: stats.episodesCount.toString(),
      color: "bg-orange-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-white rounded-lg shadow-md overflow-hidden"
        >
          <div className={`h-1 ${card.color}`} />
          <div className="p-4">
            <p className="text-gray-500 text-sm">{card.title}</p>
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            {card.subtitle && (
              <p className="text-sm text-gray-400">{card.subtitle}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
