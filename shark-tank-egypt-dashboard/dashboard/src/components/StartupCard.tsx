"use client";

import { Startup } from "@/types/startup";
import { formatCurrency, formatPercentage, cn } from "@/lib/utils";
import Link from "next/link";

interface StartupCardProps {
    startup: Startup;
}

export function StartupCard({ startup }: StartupCardProps) {
    return (
        <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
            <div className="p-6">
                <div className="flex justify-between items-start mb-3">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                            {startup.name}
                        </h3>
                        {startup.name_ar && (
                            <p className="text-sm text-gray-500 font-arabic">
                                {startup.name_ar}
                            </p>
                        )}
                    </div>
                    <span
                        className={cn(
                            "px-2 py-1 text-xs font-medium rounded-full",
                            startup.deal_made
                                ? "bg-green-100 text-green-800"
                                : "bg-red-100 text-red-800"
                        )}
                    >
                        {startup.deal_made ? "Deal" : "No Deal"}
                    </span>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                    {startup.description}
                </p>

                <div className="space-y-2 text-sm">
                    {startup.industry && (
                        <div className="flex justify-between">
                            <span className="text-gray-500">Industry:</span>
                            <span className="text-gray-900">
                                {startup.industry}
                            </span>
                        </div>
                    )}

                    <div className="flex justify-between">
                        <span className="text-gray-500">Episode:</span>
                        <span className="text-gray-900">
                            #{startup.episode_number}
                        </span>
                    </div>

                    {startup.ask_amount && (
                        <div className="flex justify-between">
                            <span className="text-gray-500">Ask:</span>
                            <span className="text-gray-900">
                                {formatCurrency(startup.ask_amount)} for{" "}
                                {formatPercentage(startup.ask_equity || 0)}
                            </span>
                        </div>
                    )}

                    {startup.deal_made && startup.deal_amount && (
                        <div className="flex justify-between text-green-700">
                            <span>Deal:</span>
                            <span>
                                {formatCurrency(startup.deal_amount)} for{" "}
                                {formatPercentage(startup.deal_equity || 0)}
                            </span>
                        </div>
                    )}

                    {/* {startup.sharks.length > 0 && (
            <div className="flex justify-between">
              <span className="text-gray-500">Sharks:</span>
              <span className="text-gray-900">{startup.sharks.join(", ")}</span>
            </div>
          )} */}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
                    {startup.website && (
                        <a
                            href={startup.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                            Website →
                        </a>
                    )}
                    <Link
                        href={startup.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-600 hover:text-gray-800 text-sm"
                    >
                        Watch Pitch →
                    </Link>
                </div>
            </div>
        </div>
    );
}
