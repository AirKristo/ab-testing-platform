/**
 * ExperimentContext — manages variant assignments and event tracking.
 *
 * WHY a dedicated context:
 * - Many components need to know "what variant am I in for experiment X?"
 * - Components also need to track events (exposure, click, conversion)
 * - Centralized logic prevents bugs (e.g., forgetting to track exposure)
 * - One source of truth for assignment caching
 *
 *
 */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import api from '../api/client.js';
import { DEMO_USER_ID } from './CartContext';

const ExperimentContext = createContext();

export function ExperimentProvider({ children }) {
  // Cache: { [experimentName]: { id, variant } }
  const [assignments, setAssignments] = useState({});
  // Catalog of running experiments by name → id
  const [experimentCatalog, setExperimentCatalog] = useState({});
  const [catalogLoaded, setCatalogLoaded] = useState(false);

  /**
   * Load the catalog of running experiments once on mount.
   * Loading the catalog lets us translate name → id transparently.
   */
  useEffect(() => {
    async function loadCatalog() {
      try {
        const response = await api.get('/experiments?status=running');
        const catalog = {};
        for (const exp of response.data.experiments) {
          catalog[exp.name] = exp.id;
        }
        setExperimentCatalog(catalog);
      } catch (error) {
        console.error('Failed to load experiment catalog:', error);
      } finally {
        setCatalogLoaded(true);
      }
    }
    loadCatalog();
  }, []);

  /**
   * Get the variant for a given experiment name.
   * Components should handle null by falling back to default behavior.
   */
  const getVariant = useCallback(async (experimentName) => {
    // Return cached value if we have one
    if (assignments[experimentName]) {
      return assignments[experimentName].variant;
    }

    // Look up the experiment ID
    const experimentId = experimentCatalog[experimentName];
    if (!experimentId) {
      // Experiment not running — component should use default
      return null;
    }

    try {
      const response = await api.get(
        `/assignments?user_id=${DEMO_USER_ID}&experiment_id=${experimentId}`
      );
      const variant = response.data.variant_name;

      // Cache the assignment
      setAssignments(prev => ({
        ...prev,
        [experimentName]: { id: experimentId, variant },
      }));

      return variant;
    } catch (error) {
      console.error(`Failed to get variant for '${experimentName}':`, error);
      return null;
    }
  }, [assignments, experimentCatalog]);

  /**
   * Track an event for an experiment.
   */
  const trackEvent = useCallback(async (
    experimentName,
    eventType,
    options = {}
  ) => {
    const experimentId = experimentCatalog[experimentName];
    if (!experimentId) {
      return; // Experiment not running — nothing to track
    }

    try {
      await api.post('/events', {
        user_id: DEMO_USER_ID,
        experiment_id: experimentId,
        event_type: eventType,
        event_value: options.value ?? null,
        event_metadata: options.metadata ?? null,
      });
    } catch (error) {
      console.error(
        `Failed to track event '${eventType}' for '${experimentName}':`,
        error
      );
    }
  }, [experimentCatalog]);

  return (
    <ExperimentContext.Provider value={{
      getVariant,
      trackEvent,
      catalogLoaded,
      assignments,
    }}>
      {children}
    </ExperimentContext.Provider>
  );
}

export function useExperiment() {
  const context = useContext(ExperimentContext);
  if (!context) {
    throw new Error('useExperiment must be used within an ExperimentProvider');
  }
  return context;
}