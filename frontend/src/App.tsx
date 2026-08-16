import { useState, useEffect } from "react";
import axios from "axios";
import { ExternalLink, GitBranch, Star, MessageSquare, Clock, Filter } from "lucide-react";

const DATA_URL = "/opportunities.json";

interface Opportunity {
  title: string;
  url: string;
  repo: string;
  stars: number;
  labels: string[];
  comments: number;
  created_at: string;
  category: string;
  category_label: string;
  category_color: string;
  career_weight: number;
  difficulty: string;
  time_estimate: string;
  score: number;
  ai_analysis: {
    summary?: string;
    first_step?: string;
    career_signal?: string;
  };
}

interface Stats {
  total: number;
  last_updated: string;
  next_update: string;
  by_category: Record<string, number>;
  by_difficulty: Record<string, number>;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  EASY: "bg-green-100 text-green-800",
  "EASY-MEDIUM": "bg-lime-100 text-lime-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  "MEDIUM-HARD": "bg-orange-100 text-orange-800",
  HARD: "bg-red-100 text-red-800",
};

export default function App() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState("all");
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(DATA_URL);
      setOpportunities(res.data.opportunities || []);
      setStats(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const filtered = opportunities.filter((o) => {
    if (selectedCategory !== "all" && o.category !== selectedCategory) return false;
    if (selectedDifficulty !== "all" && o.difficulty !== selectedDifficulty) return false;
    return true;
  });

  const categories = Array.from(new Set(opportunities.map((o) => o.category)));

  const byCategory: Record<string, number> = {};
  opportunities.forEach((o) => {
    const label = o.category_label || o.category;
    byCategory[label] = (byCategory[label] || 0) + 1;
  });

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">AI Open Source Opportunities</h1>
            <p className="text-gray-400 text-sm mt-1">
              {stats?.total || 0} opportunities from top AI organizations
            </p>
          </div>
          <div className="text-right text-xs text-gray-500">
            {stats?.last_updated && <div>Updated: {stats.last_updated}</div>}
            {stats?.next_update && <div>Next: {stats.next_update}</div>}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {Object.keys(byCategory).length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {Object.entries(byCategory).slice(0, 4).map(([cat, count]) => (
              <div key={cat} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <div className="text-2xl font-bold text-indigo-400">{count}</div>
                <div className="text-xs text-gray-400 mt-1">{cat}</div>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-gray-400" />
            <span className="text-sm text-gray-400">Filter:</span>
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat.replace(/_/g, " ")}</option>
            ))}
          </select>
          <select
            value={selectedDifficulty}
            onChange={(e) => setSelectedDifficulty(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white"
          >
            <option value="all">All Difficulties</option>
            <option value="EASY">Easy</option>
            <option value="EASY-MEDIUM">Easy-Medium</option>
            <option value="MEDIUM">Medium</option>
            <option value="MEDIUM-HARD">Medium-Hard</option>
            <option value="HARD">Hard</option>
          </select>
          <span className="text-sm text-gray-400 self-center">{filtered.length} results</span>
        </div>

        {loading && (
          <div className="text-center py-20 text-gray-400">
            <div className="animate-spin mx-auto mb-4 w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full"></div>
            <p>Loading opportunities...</p>
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            <GitBranch className="mx-auto mb-4 opacity-30" size={48} />
            <p className="text-lg">No opportunities found yet</p>
            <p className="text-sm mt-2">Data updates every 5 hours automatically</p>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((opp, i) => (
              <div
                key={i}
                onClick={() => setSelectedOpp(opp)}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-indigo-500 cursor-pointer transition group"
              >
                <div className="flex items-center justify-between mb-3">
                  <span
                    className="text-xs font-medium px-2 py-1 rounded-full"
                    style={{ backgroundColor: opp.category_color + "20", color: opp.category_color }}
                  >
                    {opp.category_label}
                  </span>
                  <span className="text-xs font-bold text-indigo-400">Score: {opp.score}</span>
                </div>
                <h3 className="font-semibold text-white text-sm leading-snug mb-3 line-clamp-2 group-hover:text-indigo-300 transition">
                  {opp.title}
                </h3>
                {opp.ai_analysis?.summary && (
                  <p className="text-xs text-gray-400 mb-3 line-clamp-2">{opp.ai_analysis.summary}</p>
                )}
                <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                  <GitBranch size={12} />
                  <span className="truncate">{opp.repo}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Star size={11} />
                    {opp.stars.toLocaleString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare size={11} />
                    {opp.comments}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    {opp.time_estimate}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${DIFFICULTY_COLORS[opp.difficulty] || "bg-gray-700 text-gray-300"}`}>
                    {opp.difficulty}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedOpp && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedOpp(null)}
        >
          <div
            className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <span
                className="text-xs font-medium px-2 py-1 rounded-full"
                style={{ backgroundColor: selectedOpp.category_color + "20", color: selectedOpp.category_color }}
              >
                {selectedOpp.category_label}
              </span>
              <button
                onClick={() => setSelectedOpp(null)}
                className="text-gray-500 hover:text-white text-xl leading-none"
              >
                x
              </button>
            </div>

            <h2 className="text-lg font-bold text-white mb-4">{selectedOpp.title}</h2>

            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-indigo-400">{selectedOpp.score}</div>
                <div className="text-xs text-gray-400">Career Score</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-green-400">{selectedOpp.difficulty}</div>
                <div className="text-xs text-gray-400">Difficulty</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-yellow-400">{selectedOpp.time_estimate}</div>
                <div className="text-xs text-gray-400">Estimate</div>
              </div>
            </div>

            {selectedOpp.ai_analysis?.summary && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">What needs to be done</h3>
                <p className="text-sm text-gray-400">{selectedOpp.ai_analysis.summary}</p>
              </div>
            )}

            {selectedOpp.ai_analysis?.first_step && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">First Step</h3>
                <p className="text-sm text-gray-400">{selectedOpp.ai_analysis.first_step}</p>
              </div>
            )}

            {selectedOpp.ai_analysis?.career_signal && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Career Signal</h3>
                <p className="text-sm text-gray-400">{selectedOpp.ai_analysis.career_signal}</p>
              </div>
            )}

            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Labels</h3>
              <div className="flex flex-wrap gap-2">
                {selectedOpp.labels.length > 0 ? selectedOpp.labels.map((l, idx) => (
                  <span key={idx} className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded">{l}</span>
                )) : <span className="text-gray-500 text-xs">No labels</span>}
              </div>
            </div>

            <div className="flex items-center gap-3 pt-4 border-t border-gray-800">
              <a
                href={selectedOpp.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg text-sm font-medium transition flex-1 justify-center"
              >
                <ExternalLink size={16} />
                View on GitHub
              </a>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Star size={12} />
                  {selectedOpp.stars.toLocaleString()}
                </span>
                <span className="flex items-center gap-1">
                  <MessageSquare size={12} />
                  {selectedOpp.comments}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}