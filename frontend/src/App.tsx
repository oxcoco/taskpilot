import { useState, useEffect } from 'react';
import './App.css';

interface Task {
  id: string;
  title: string;
  description: string;
  deadline: string | null;
  priority: string;
  estimated_hours: number;
  status: string;
}

interface Schedule {
  [day: string]: string[];
}

interface ToastMessage {
  id: string;
  text: string;
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [schedule, setSchedule] = useState<Schedule>({});
  const [weeklyPlan, setWeeklyPlan] = useState<string>('');
  const [deadlineOutput, setDeadlineOutput] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  // Form Fields
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [deadline, setDeadline] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [estHours, setEstHours] = useState('1.0');

  // NLP Input
  const [nlpInput, setNlpInput] = useState('');

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (text: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const API_BASE = 'http://127.0.0.1:5000/api';

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      if (!res.ok) throw new Error('Failed to fetch tasks');
      const data = await res.json();
      setTasks(data);
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schedule`);
      if (!res.ok) throw new Error('Failed to fetch schedule');
      const data = await res.json();
      setSchedule(data);
      showToast('Schedule generated successfully');
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchWeeklyPlan = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/weekly_plan`);
      if (!res.ok) throw new Error('Failed to generate weekly plan');
      const data = await res.json();
      setWeeklyPlan(data.plan);
      showToast('Weekly plan generated');
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const triggerDeadlineCheck = async () => {
    try {
      const res = await fetch(`${API_BASE}/check_deadlines`, { method: 'POST' });
      if (!res.ok) throw new Error('Deadline check failed');
      const data = await res.json();
      setDeadlineOutput(data.output);
      showToast('Deadlines checked');
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleNlpAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlpInput.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: nlpInput }),
      });
      if (!res.ok) throw new Error('Failed to parse and add task');
      showToast('Task added via NLP!');
      setNlpInput('');
      fetchTasks();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          deadline: deadline || null,
          priority,
          estimated_hours: parseFloat(estHours) || 1.0,
        }),
      });
      if (!res.ok) throw new Error('Failed to create task');
      showToast('Task created successfully');
      setShowAddModal(false);
      resetForm();
      fetchTasks();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleUpdateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTask) return;
    try {
      const res = await fetch(`${API_BASE}/tasks/${activeTask.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          deadline: deadline || null,
          priority,
          estimated_hours: parseFloat(estHours) || 1.0,
        }),
      });
      if (!res.ok) throw new Error('Failed to update task');
      showToast('Task updated successfully');
      setShowEditModal(false);
      resetForm();
      fetchTasks();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const toggleTaskStatus = async (task: Task) => {
    const isCompleted = task.status === 'COMPLETED';
    const endpoint = isCompleted ? 'undone' : 'done';
    try {
      const res = await fetch(`${API_BASE}/tasks/${task.id}/${endpoint}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to toggle status');
      showToast(`Task marked as ${isCompleted ? 'pending' : 'completed'}`);
      fetchTasks();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const deleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete task');
      showToast('Task deleted');
      fetchTasks();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const clearAllTasks = async () => {
    if (!confirm('WARNING: Are you sure you want to delete ALL tasks?')) return;
    try {
      const res = await fetch(`${API_BASE}/tasks`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete tasks');
      showToast('All tasks deleted');
      setTasks([]);
      setSchedule({});
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const openEditModal = (task: Task) => {
    setActiveTask(task);
    setTitle(task.title);
    setDescription(task.description || '');
    setDeadline(task.deadline || '');
    setPriority(task.priority);
    setEstHours(task.estimated_hours.toString());
    setShowEditModal(true);
  };

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setDeadline('');
    setPriority('MEDIUM');
    setEstHours('1.0');
    setActiveTask(null);
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const pendingTasks = tasks.filter((t) => t.status !== 'COMPLETED');
  const completedTasks = tasks.filter((t) => t.status === 'COMPLETED');

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <h1>⚡ TaskPilot</h1>
          <div className="brand-subtitle">Smart agentic task scheduler & planner</div>
        </div>
        <div className="global-actions">
          <button className="btn btn-secondary" onClick={triggerDeadlineCheck}>
            Check Deadlines
          </button>
          <button className="btn btn-secondary" onClick={fetchWeeklyPlan}>
            Weekly Plan
          </button>
          <button className="btn btn-danger" onClick={clearAllTasks}>
            Clear All
          </button>
        </div>
      </header>

      {/* NLP Bar */}
      <section className="panel-card">
        <form onSubmit={handleNlpAdd} className="quick-add-form">
          <input
            type="text"
            className="quick-add-input"
            placeholder="Describe a task in natural language... (e.g. Finish chemistry project by Friday at 5pm)"
            value={nlpInput}
            onChange={(e) => setNlpInput(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">
            Quick Add
          </button>
        </form>
      </section>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <div className="main-column">
          {/* Tasks List */}
          <section className="panel-card">
            <div className="panel-title">
              Tasks
              <button
                className="btn btn-primary btn-secondary"
                onClick={() => {
                  resetForm();
                  setShowAddModal(true);
                }}
              >
                +
              </button>
            </div>

            <div className="tasks-container">
              {pendingTasks.map((task) => (
                <div className="task-item" key={task.id}>
                  <div
                    className="task-checkbox"
                    onClick={() => toggleTaskStatus(task)}
                  />
                  <div className="task-details">
                    <h3 className="task-title">{task.title}</h3>
                    <div className="task-meta">
                      <span className={`task-badge badge-${task.priority.toLowerCase()}`}>
                        {task.priority}
                      </span>
                      {task.deadline && (
                        <span className="task-deadline">
                          Due by: {task.deadline}
                        </span>
                      )}
                      <span className="task-hours">
                        ⏱ {task.estimated_hours}h
                      </span>
                      {task.description && (
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                          {task.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="task-actions">
                    <button className="btn btn-secondary btn-icon-only" onClick={() => openEditModal(task)}>
                      Edit
                    </button>
                    <button className="btn btn-danger btn-icon-only" onClick={() => deleteTask(task.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}

              {completedTasks.length > 0 && (
                <div style={{ marginTop: '20px', borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                    Completed Tasks
                  </div>
                  {completedTasks.map((task) => (
                    <div className="task-item completed" key={task.id}>
                      <div
                        className="task-checkbox checked"
                        onClick={() => toggleTaskStatus(task)}
                      />
                      <div className="task-details">
                        <h3 className="task-title">{task.title}</h3>
                        <div className="task-meta">
                          <span className={`task-badge badge-${task.priority.toLowerCase()}`}>
                            {task.priority}
                          </span>
                        </div>
                      </div>
                      <div className="task-actions">
                        <button className="btn btn-danger btn-icon-only" onClick={() => deleteTask(task.id)}>
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {tasks.length === 0 && (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
                  No tasks found. Try typing one in the input box above!
                </div>
              )}
            </div>
          </section>

          {/* Schedule View */}
          <section className="panel-card">
            <div className="panel-title">
              Generated Schedule
              <button className="btn btn-secondary" onClick={fetchSchedule} disabled={loading}>
                Generate / Refresh Schedule
              </button>
            </div>
            {Object.keys(schedule).length > 0 ? (
              <div className="schedule-grid">
                {Object.entries(schedule).map(([day, items]) => (
                  <div className={`schedule-day-card ${day === 'Completed' ? 'completed-day' : ''}`} key={day}>
                    <h4 className="schedule-day-title" style={day === 'Completed' ? { color: 'var(--status-completed)' } : {}}>{day}</h4>
                    <div className="schedule-item-list">
                      {items.map((item, idx) => (
                        <div
                          className="schedule-task-title"
                          style={day === 'Completed' ? { borderLeftColor: 'var(--status-completed)', textDecoration: 'line-through', opacity: 0.7 } : {}}
                          key={idx}
                        >
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
                No schedule generated yet. Click "Generate / Refresh Schedule" to construct a priority-based timeline.
              </div>
            )}
          </section>
        </div>

        {/* Right Column / Panels */}
        <div className="main-column">
          {/* Weekly Plan */}
          <section className="panel-card">
            <div className="panel-title">Weekly Assistant Plan</div>
            {weeklyPlan ? (
              <pre className="weekly-plan-text">{weeklyPlan}</pre>
            ) : (
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', padding: '20px 0' }}>
                Click "Weekly Plan" at the top to generate a personalized weekly summary using GPT-4.
              </div>
            )}
          </section>

          {/* Deadline Check Status */}
          <section className="panel-card">
            <div className="panel-title">Deadline Status</div>
            {deadlineOutput ? (
              <pre className="weekly-plan-text" style={{ maxHeight: '200px' }}>{deadlineOutput}</pre>
            ) : (
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', padding: '20px 0' }}>
                Click "Check Deadlines" at the top to view overdue and upcoming tasks.
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Add Task Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontFamily: 'var(--heading)', marginBottom: '20px' }}>Add Task</h2>
            <form onSubmit={handleCreateTask}>
              <div className="form-group">
                <label className="form-label">Title</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description (optional)</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Deadline (e.g. 2026-12-31, today, tomorrow)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="2026-06-30"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Priority</label>
                  <select
                    className="form-control"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Est. Hours</label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-control"
                    value={estHours}
                    onChange={(e) => setEstHours(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Task Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontFamily: 'var(--heading)', marginBottom: '20px' }}>Edit Task</h2>
            <form onSubmit={handleUpdateTask}>
              <div className="form-group">
                <label className="form-label">Title</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description (optional)</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Deadline</label>
                <input
                  type="text"
                  className="form-control"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Priority</label>
                  <select
                    className="form-control"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Est. Hours</label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-control"
                    value={estHours}
                    onChange={(e) => setEstHours(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Update Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification Area */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div className="toast" key={toast.id}>
            {toast.text}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
