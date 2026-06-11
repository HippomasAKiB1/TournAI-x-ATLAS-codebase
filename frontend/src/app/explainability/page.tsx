"use client";

import React, { useEffect, useState } from "react";
import { useTournament } from "../../context/TournamentContext";
import { getExplanations, getModelComparison } from "../../lib/api";
import {
  Brain,
  Cpu,
  Loader2,
  Info
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer
} from "recharts";

export default function ExplainabilityPage() {
  const { loading: contextLoading } = useTournament();
  const [explanations, setExplanations] = useState<any>(null);
  const [modelComparison, setModelComparison] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchExplainDetails = async () => {
      try {
        const [exp, comp] = await Promise.all([
          getExplanations(),
          getModelComparison()
        ]);
        setExplanations(exp);
        setModelComparison(comp);
      } catch (err) {
        console.error("Failed to load explainability metrics:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchExplainDetails();
  }, []);

  if (contextLoading || loading || !explanations || !modelComparison) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20">
        <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
        <p className="text-sm text-zinc-400 font-medium">Opening SHAP Explainability & Performance Hub...</p>
      </div>
    );
  }

  const fiData = (explanations.feature_importance || []).slice(0, 10).map((item: any) => ({
    name: item.feature,
    value: item.shap_importance * 100,
  }));

  const models = modelComparison.models || [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <Brain className="h-8 w-8 text-purple-400" /> Explainability & Performance Hub
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Explore global feature importance vectors and check model calibration statistics on the test set.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Global SHAP Feature Importance */}
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl min-w-0">
          <div className="mb-4">
            <h4 className="text-base font-bold text-white">Global SHAP Feature Importance</h4>
            <p className="text-xs text-zinc-400">Average impact of top features on outcome predictions.</p>
          </div>
          <div className="h-96 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={fiData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
              >
                <XAxis type="number" stroke="#71717a" fontSize={11} unit="%" />
                <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={10} width={100} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(2)}%`, "SHAP Importance"]}
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    color: "#f4f4f7",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="value" fill="#a855f7" radius={[0, 4, 4, 0]}>
                  {fiData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? "#8b5cf6" : "#06b6d4"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feature dictionary glossary */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <h4 className="text-base font-bold text-white mb-1">Feature Glossary</h4>
            <p className="text-xs text-zinc-400 mb-6">Definitions of key features driving the ATLAS classifier.</p>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">opp_conf_code</span>
                <p className="text-zinc-400 text-[11px]">Confederation profile code of the opponent (UEFA, CONMEBOL, CAF, etc.).</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">is_knockout</span>
                <p className="text-zinc-400 text-[11px]">Flag indicating if the match is in a knockout stage, where draw rates collapse to zero.</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">elo_diff</span>
                <p className="text-zinc-400 text-[11px]">Difference in Elo ratings between the team and its opponent.</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">squad_quality_diff</span>
                <p className="text-zinc-400 text-[11px]">Computed average impact score gap based on underlying club prestige statistics.</p>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Performance Matrix */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-zinc-800">
          <h4 className="text-base font-bold text-white">ATLAS Model Performance Matrix</h4>
          <p className="text-xs text-zinc-400">Comparing test set metrics (World Cup 2022 fixtures) across candidate classifiers.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider font-mono">
                <th className="py-3.5 px-6">Model</th>
                <th className="py-3.5 px-4 text-center">Accuracy</th>
                <th className="py-3.5 px-4 text-center">Log Loss</th>
                <th className="py-3.5 px-4 text-center">Brier Score</th>
                <th className="py-3.5 px-4 text-center">ROC AUC</th>
                <th className="py-3.5 px-4 text-center">F1 Weighted</th>
                <th className="py-3.5 px-4 text-center">MCC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {models.map((model: any) => {
                const isBest = model.Model === modelComparison.best_model;
                return (
                  <tr key={model.Model} className={`hover:bg-zinc-900/10 transition ${isBest ? "bg-cyan-950/5 text-cyan-200" : ""}`}>
                    <td className="py-3 px-6 font-semibold flex items-center gap-2">
                      {isBest && <Cpu className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />}
                      <span className={isBest ? "text-cyan-400 font-bold" : "text-white"}>{model.Model}</span>
                    </td>
                    <td className={`py-3 px-4 text-center font-mono ${isBest ? "font-bold text-cyan-400" : ""}`}>
                      {(model.Accuracy * 100).toFixed(2)}%
                    </td>
                    <td className="py-3 px-4 text-center font-mono">{model["Log Loss"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["Brier Score"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["ROC AUC"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["F1 Weighted"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model.MCC?.toFixed(3)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
