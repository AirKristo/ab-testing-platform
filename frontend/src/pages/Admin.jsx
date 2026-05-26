/**
 * Admin panel — view and manage experiments.
 */
import { useState, useEffect } from 'react';
import api from '../api/client';
import ExperimentResults from '../components/ExperimentResults';

const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-700',
  running: 'bg-green-100 text-green-700',
  paused: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-indigo-100 text-indigo-700',
};

export default function Admin() {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchExperiments = async () => {
    try {
      setLoading(true);
      const response = await api.get('/experiments');
      setExperiments(response.data.experiments);
    } catch (err) {
      setError('Failed to load experiments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  // Status transition handlers
  const handleAction = async (experimentId, action) => {
    try {
      await api.post(`/experiments/${experimentId}/${action}`);
      await fetchExperiments();
    } catch (err) {
      alert(`Failed to ${action} experiment: ${err.response?.data?.detail || err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center text-gray-500">
        {error}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Experiments</h1>
      <p className="text-sm text-gray-500 mb-8">
        Manage running experiments and view their configuration.
      </p>

      {experiments.length === 0 ? (
        <div className="text-center py-16 bg-white border border-gray-200 rounded-lg">
          <p className="text-gray-500">No experiments yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {experiments.map(exp => (
            <ExperimentCard
              key={exp.id}
              experiment={exp}
              onAction={handleAction}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ExperimentCard({ experiment, onAction }) {
  const { id, name, description, status, variants, metrics, start_date, end_date } = experiment;
  const [showResults, setShowResults] = useState(false);

  // Only show results for experiments that have started
  const hasData = status === 'running' || status === 'paused' || status === 'completed';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-lg font-semibold text-gray-900">{name}</h2>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[status]}`}>
              {status}
            </span>
          </div>
          {description && (
            <p className="text-sm text-gray-500 mb-2">{description}</p>
          )}
          <p className="text-xs text-gray-400">
            ID: {id}
            {start_date && ` • Started: ${new Date(start_date).toLocaleDateString()}`}
            {end_date && ` • Ended: ${new Date(end_date).toLocaleDateString()}`}
          </p>
        </div>

        <div className="flex gap-2">
          {status === 'draft' && (
            <button
              onClick={() => onAction(id, 'start')}
              className="bg-green-600 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-green-700 transition-colors"
            >
              Start
            </button>
          )}
          {status === 'running' && (
            <>
              <button
                onClick={() => onAction(id, 'pause')}
                className="bg-yellow-500 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-yellow-600 transition-colors"
              >
                Pause
              </button>
              <button
                onClick={() => onAction(id, 'complete')}
                className="bg-gray-700 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-gray-800 transition-colors"
              >
                Complete
              </button>
            </>
          )}
          {status === 'paused' && (
            <>
              <button
                onClick={() => onAction(id, 'start')}
                className="bg-green-600 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-green-700 transition-colors"
              >
                Resume
              </button>
              <button
                onClick={() => onAction(id, 'complete')}
                className="bg-gray-700 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-gray-800 transition-colors"
              >
                Complete
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-100">
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Variants
          </h3>
          <div className="space-y-1">
            {variants.map(v => (
              <div key={v.name} className="flex justify-between text-sm">
                <span className="text-gray-700">{v.name}</span>
                <span className="text-gray-500 font-mono">
                  {(v.allocation * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Metrics
          </h3>
          <p className="text-sm text-gray-700">
            <span className="font-medium">Primary:</span> {metrics.primary}
          </p>
          {metrics.secondary && metrics.secondary.length > 0 && (
            <p className="text-sm text-gray-700">
              <span className="font-medium">Secondary:</span> {metrics.secondary.join(', ')}
            </p>
          )}
        </div>
      </div>

      {hasData && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <button
            onClick={() => setShowResults(!showResults)}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            {showResults ? '▼ Hide Results' : '▶ View Statistical Results'}
          </button>
          {showResults && (
            <div className="mt-3">
              <ExperimentResults
                experimentId={id}
                defaultMetric={metrics.primary}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}