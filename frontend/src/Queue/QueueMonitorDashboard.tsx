import React, { useState, useEffect } from 'react';
import { backendUrl } from '../env';
import './queue-monitor-dashboard.css';

interface TrackedProject {
  tracking_id: string;
  project_name: string;
  rto: string;
  queue_id: string;
  initial_position?: number;
  current_phase: string;
  tracking_started_at: string;
  alerts: Alert[];
}

interface Alert {
  type: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  due_date?: string;
  amount?: number;
}

interface MonitoringForm {
  rto: string;
  queue_id: string;
  project_name: string;
}

export const QueueMonitorDashboard: React.FC = () => {
  const [trackedProjects, setTrackedProjects] = useState<TrackedProject[]>([]);
  const [form, setForm] = useState<MonitoringForm>({
    rto: 'ERCOT',
    queue_id: '',
    project_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setTrackedProjects([]);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(backendUrl('/queue/monitor-queue'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        throw new Error('Failed to add project to monitoring');
      }

      const body = await response.json();
      const newProject: TrackedProject = {
        tracking_id: body.tracking_id,
        project_name: body.project_name,
        rto: body.rto,
        queue_id: form.queue_id,
        initial_position: body.queue_position ?? undefined,
        current_phase: body.current_phase,
        tracking_started_at: new Date().toISOString(),
        alerts: Array.isArray(body.alerts) ? body.alerts : [],
      };
      setTrackedProjects(prev => [...prev, newProject]);
      setForm({ rto: 'ERCOT', queue_id: '', project_name: '' });
      setSuccess(`Successfully monitoring: ${form.project_name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'high':
        return '#dc3545';
      case 'medium':
        return '#ffc107';
      default:
        return '#28a745';
    }
  };

  return (
    <div className="queue-monitor-dashboard">
      <div className="monitor-container">
        <h1>Interconnection Queue Monitor</h1>
        <p className="subtitle">Track your projects through RTO queues and receive alerts on key milestones</p>

        {/* Add Project Form */}
        <div className="add-project-section">
          <h2>Add Project to Monitoring</h2>
          <form onSubmit={handleAddProject} className="monitor-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="project_name">Project Name *</label>
                <input
                  id="project_name"
                  type="text"
                  name="project_name"
                  value={form.project_name}
                  onChange={handleInputChange}
                  placeholder="e.g., Acme Solar Farm Phase 1"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="rto">RTO/ISO *</label>
                <select
                  id="rto"
                  name="rto"
                  value={form.rto}
                  onChange={handleInputChange}
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
                <label htmlFor="queue_id">Queue ID/Position *</label>
                <input
                  id="queue_id"
                  type="text"
                  name="queue_id"
                  value={form.queue_id}
                  onChange={handleInputChange}
                  placeholder="e.g., 12345"
                  required
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Adding to Monitor...' : 'Add to Monitor'}
            </button>
          </form>

          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
        </div>

        {/* Tracked Projects */}
        <div className="tracked-projects-section">
          <h2>Tracked Projects ({trackedProjects.length})</h2>

          {trackedProjects.length === 0 ? (
            <div className="empty-state">
              <p>No projects being monitored yet. Add a project above to get started.</p>
            </div>
          ) : (
            <div className="projects-grid">
              {trackedProjects.map(project => (
                <div key={project.tracking_id} className="project-card">
                  <div className="project-header">
                    <h3>{project.project_name}</h3>
                    <span className="rto-badge">{project.rto}</span>
                  </div>

                  <div className="project-details">
                    <div className="detail-row">
                      <span className="label">Queue Position:</span>
                      <span className="value">{project.initial_position ?? 'Not stated on the cited file'}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">Current Phase:</span>
                      <span className="value phase-badge">{project.current_phase}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">Monitoring Since:</span>
                      <span className="value">
                        {new Date(project.tracking_started_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {/* Alerts */}
                  {project.alerts.length > 0 && (
                    <div className="alerts-section">
                      <h4>Active Alerts ({project.alerts.length})</h4>
                      {project.alerts.map((alert, idx) => (
                        <div
                          key={idx}
                          className="alert-item"
                          style={{ borderLeftColor: getPriorityColor(alert.priority) }}
                        >
                          <div className="alert-title">
                            <span className="priority-badge" style={{ backgroundColor: getPriorityColor(alert.priority) }}>
                              {alert.priority.toUpperCase()}
                            </span>
                            {alert.title}
                          </div>
                          <p className="alert-description">{alert.description}</p>
                          {alert.due_date && (
                            <p className="alert-meta">
                              Due: {new Date(alert.due_date).toLocaleDateString()}
                            </p>
                          )}
                          {alert.amount && (
                            <p className="alert-meta">
                              Amount: ${(alert.amount).toLocaleString()}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {project.alerts.length === 0 && (
                    <div className="no-alerts">
                      <p>✓ No active alerts</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QueueMonitorDashboard;
