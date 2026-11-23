import React, { useState } from 'react';
import { backendUrl } from '../env';
import './timeline-predictor.css';

interface TimelineProjection {
  rto: string;
  project_capacity_mw: number;
  study_track: string;
  predicted_study_completion: string;
  predicted_energization_date: string;
  confidence_interval_days: number;
  comparable_projects: ComparableProject[];
  timeline_summary: string;
}

interface ComparableProject {
  capacity_mw: number;
  study_duration_months: number;
  total_timeline_months: number;
}

export const TimelinePredictor: React.FC = () => {
  const [rto, setRto] = useState('PJM');
  const [capacity, setCapacity] = useState(100);
  const [queuePosition, setQueuePosition] = useState('');
  const [studyTrack, setStudyTrack] = useState('Standard');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projection, setProjection] = useState<TimelineProjection | null>(null);


  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setProjection(null);

    try {
      const params = new URLSearchParams({
        rto,
        project_capacity_mw: capacity.toString(),
        study_track: studyTrack,
      });

      if (queuePosition) {
        params.append('queue_position', queuePosition);
      }

      const response = await fetch(`${backendUrl('/queue/predict-timeline')}?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();
      if (!response.ok || !data.predicted_energization_date) {
        throw new Error(
          data.note || data.detail || 'The official queue file does not state an energization date. No date is estimated.'
        );
      }

      setProjection(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const calculateMonths = (date: string) => {
    const target = new Date(date);
    const now = new Date();
    const months = (target.getFullYear() - now.getFullYear()) * 12 + (target.getMonth() - now.getMonth());
    return Math.max(0, months);
  };

  return (
    <div className="timeline-predictor">
      <div className="predictor-container">
        <h1>Interconnection Timeline Predictor</h1>
        <p className="subtitle">The official queue file does not state an energization date. No date is estimated.</p>

        <div className="predictor-content">
          {/* Input Section */}
          <div className="input-section">
            <h2>Project Parameters</h2>

            <form onSubmit={handlePredict} className="prediction-form">
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="rto">RTO/ISO *</label>
                  <select
                    id="rto"
                    value={rto}
                    onChange={(e) => setRto(e.target.value)}
                    required
                  >
                    <option value="PJM">PJM</option>
                    <option value="MISO">MISO</option>
                    <option value="ERCOT">ERCOT</option>
                    <option value="CAISO">CAISO</option>
                    <option value="SPP">SPP</option>
                    <option value="NYISO">NYISO</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="capacity">Project Capacity (MW) *</label>
                  <input
                    id="capacity"
                    type="number"
                    value={capacity}
                    onChange={(e) => setCapacity(parseFloat(e.target.value))}
                    min="1"
                    max="500"
                    step="10"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="study_track">Study Track</label>
                  <select
                    id="study_track"
                    value={studyTrack}
                    onChange={(e) => setStudyTrack(e.target.value)}
                  >
                    <option value="Standard">Standard (24+ months)</option>
                    <option value="Expedited">Expedited (12-15 months)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="queue_position">Queue Position (Optional)</label>
                  <input
                    id="queue_position"
                    type="number"
                    value={queuePosition}
                    onChange={(e) => setQueuePosition(e.target.value)}
                    placeholder="e.g., 50"
                    min="1"
                  />
                </div>
              </div>

              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Predicting Timeline...' : 'Predict Timeline'}
              </button>
            </form>

            {error && <div className="alert alert-error">{error}</div>}
          </div>

          {/* Results Section */}
          {projection && (
            <div className="results-section">
              <h2>Timeline Projection</h2>

              {/* Timeline Visual */}
              <div className="timeline-visualization">
                <div className="timeline-header">
                  <span>Today</span>
                  <span>Study Complete</span>
                  <span>Energization</span>
                </div>

                <div className="timeline-track">
                  <div className="timeline-marker start" />
                  <div
                    className="timeline-progress study"
                    style={{
                      width: `${(calculateMonths(projection.predicted_study_completion) / calculateMonths(projection.predicted_energization_date)) * 100}%`,
                    }}
                  />
                  <div
                    className="timeline-progress construction"
                    style={{
                      width: `${(100 - (calculateMonths(projection.predicted_study_completion) / calculateMonths(projection.predicted_energization_date)) * 100)}%`,
                    }}
                  />
                  <div className="timeline-marker end" />
                </div>

                <div className="timeline-labels">
                  <div className="label-group">
                    <span className="label-badge study-badge">Study Phase</span>
                    <span className="label-months">~{calculateMonths(projection.predicted_study_completion)} months</span>
                  </div>
                  <div className="label-group">
                    <span className="label-badge construction-badge">Construction/Commissioning</span>
                    <span className="label-months">~{calculateMonths(projection.predicted_energization_date) - calculateMonths(projection.predicted_study_completion)} months</span>
                  </div>
                </div>
              </div>

              {/* Key Projections */}
              <div className="key-projections">
                <div className="projection-card">
                  <h3>Predicted Study Completion</h3>
                  <div className="date-large">
                    {new Date(projection.predicted_study_completion).toLocaleDateString('en-US', {
                      month: 'long',
                      year: 'numeric',
                    })}
                  </div>
                  <p className="months-to">
                    {calculateMonths(projection.predicted_study_completion)} months from now
                  </p>
                </div>

                <div className="projection-card highlight">
                  <h3>Predicted Energization Date</h3>
                  <div className="date-large energization">
                    {new Date(projection.predicted_energization_date).toLocaleDateString('en-US', {
                      month: 'long',
                      year: 'numeric',
                    })}
                  </div>
                  <p className="months-to">
                    {calculateMonths(projection.predicted_energization_date)} months from now
                  </p>
                  <p className="confidence">
                    ±{projection.confidence_interval_days} days confidence interval
                  </p>
                </div>

                <div className="projection-card">
                  <h3>Total Timeline</h3>
                  <div className="months-display">
                    ~{calculateMonths(projection.predicted_energization_date)} months
                  </div>
                  <p className="timeline-text">From today to energization</p>
                </div>
              </div>

              {/* Comparable Projects */}
              {projection.comparable_projects.length > 0 && (
                <div className="comparables-section">
                  <h3>Historical Comparable Projects</h3>
                  <div className="comparables-table">
                    <div className="table-header">
                      <div className="col">Capacity</div>
                      <div className="col">Study Duration</div>
                      <div className="col">Total Timeline</div>
                    </div>
                    {projection.comparable_projects.map((proj, idx) => (
                      <div key={idx} className="table-row">
                        <div className="col">{proj.capacity_mw} MW</div>
                        <div className="col">{proj.study_duration_months} months</div>
                        <div className="col">{proj.total_timeline_months} months</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Summary */}
              <div className="summary-section">
                <h3>Analysis Summary</h3>
                <div className="summary-box">
                  {projection.timeline_summary}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TimelinePredictor;
