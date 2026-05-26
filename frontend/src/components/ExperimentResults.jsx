/**
 * ExperimentResults component — statistical analysis display.
 *
 * Shows per-variant metrics and statistical comparisons.
 */
import { useEffect, useState } from 'react';
import api from '../api/client';

// Available metrics that can be analyzed
const SUPPORTED_METRICS = [
  { value: 'conversion_rate', label: 'Conversion Rate', format: 'percent' },
  { value: 'add_to_cart_rate', label: 'Add to Cart Rate', format: 'percent' },
  { value: 'click_through_rate', label: 'Click-Through Rate', format: 'percent' },
  { value: 'revenue_per_user', label: 'Revenue per User', format: 'currency' },
];

const formatValue = (value, format) => {
  if (format === 'percent') return `${(value * 100).toFixed(2)}%`;
  if (format === 'currency') return `$${value.toFixed(2)}`;
  return value.toFixed(4);
};

const formatRelative = (value) => {
  const pct = value * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
};

export default function ExperimentResults({ experimentId, defaultMetric }) {
  const [selectedMetric, setSelectedMetric] = useState(defaultMetric || 'conversion_rate');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchResults() {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get(
          `/experiments/${experimentId}/results?metric=${selectedMetric}`
        );
        setResults(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load results');
      } finally {
        setLoading(false);
      }
    }
    fetchResults();
  }, [experimentId, selectedMetric]);

  const metricConfig = SUPPORTED_METRICS.find(m => m.value === selectedMetric);
  const formatFn = metricConfig?.format || 'decimal';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-900">Statistical Results</h3>
        <select
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {SUPPORTED_METRICS.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="animate-pulse space-y-3">
          <div className="h-12 bg-gray-100 rounded" />
          <div className="h-12 bg-gray-100 rounded" />
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
          {error}
        </div>
      )}

      {!loading && !error && results && (
        <>
          {/* Per-variant metrics table */}
          <div className="overflow-hidden border border-gray-200 rounded-lg mb-4">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Variant</th>
                  <th className="px-4 py-2 text-right">Sample Size</th>
                  <th className="px-4 py-2 text-right">Mean</th>
                  <th className="px-4 py-2 text-right">95% CI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.metrics.map((m) => (
                  <tr key={m.variant_name}>
                    <td className="px-4 py-2 font-medium text-gray-900">
                      {m.variant_name}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-700 font-mono">
                      {m.sample_size}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-900 font-mono font-semibold">
                      {formatValue(m.mean, formatFn)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500 font-mono text-xs">
                      [{formatValue(m.ci_lower, formatFn)}, {formatValue(m.ci_upper, formatFn)}]
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Statistical tests */}
          {results.tests.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Pairwise Comparisons (vs. {results.tests[0].control_variant})
              </h4>
              {results.tests.map((test) => (
                <TestResultCard key={test.treatment_variant} test={test} formatFn={formatFn} />
              ))}
            </div>
          )}

          {results.tests.length === 0 && (
            <p className="text-sm text-gray-500 italic">
              Not enough data yet for a statistical test. Need at least 2 users per variant.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function TestResultCard({ test, formatFn }) {
  const { treatment_variant, p_value, absolute_effect, relative_effect,
          ci_lower, ci_upper, is_significant } = test;

  const direction = absolute_effect > 0 ? 'increase' : 'decrease';
  const sigColor = is_significant
    ? (absolute_effect > 0 ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50')
    : 'text-gray-700 bg-gray-50';

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-sm font-semibold text-gray-900">{treatment_variant}</p>
          <p className="text-xs text-gray-500">vs. control</p>
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${sigColor}`}>
          {is_significant ? `Significant ${direction}` : 'Not significant'}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Effect</p>
          <p className="font-mono font-semibold text-gray-900">
            {formatValue(absolute_effect, formatFn)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Relative</p>
          <p className="font-mono font-semibold text-gray-900">
            {formatRelative(relative_effect)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">p-value</p>
          <p className="font-mono font-semibold text-gray-900">
            {p_value < 0.001 ? '<0.001' : p_value.toFixed(4)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">95% CI</p>
          <p className="font-mono text-xs text-gray-700">
            [{formatValue(ci_lower, formatFn)}, {formatValue(ci_upper, formatFn)}]
          </p>
        </div>
      </div>
    </div>
  );
}