const { useState, useEffect, useMemo } = React;

const API_BASE = '/api';

// ── API Service ─────────────────────────────────────────────────────────────
const api = {
    getStats: async () => {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        return res.json();
    },
    getUsers: async () => {
        const res = await fetch(`${API_BASE}/users`);
        if (!res.ok) throw new Error('Failed to fetch users');
        return res.json();
    },
    updateUser: async (id, data) => {
        const res = await fetch(`${API_BASE}/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Failed to update user');
        return res.json();
    },
    deleteUser: async (id) => {
        const res = await fetch(`${API_BASE}/users/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete user');
        return res.json();
    }
};

// ── Components ──────────────────────────────────────────────────────────────

function StatCard({ title, value, icon, color, delay }) {
    return (
        <div className={`glass-panel rounded-xl p-5 flex items-center justify-between animate-fade-in ${delay}`}>
            <div>
                <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
                <h3 className="text-3xl font-bold text-white">{value}</h3>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center bg-${color}-500/20 text-${color}-400`}>
                <i className={`fas fa-${icon} text-xl`}></i>
            </div>
        </div>
    );
}

function UserModal({ user, onClose, onSave }) {
    const [formData, setFormData] = useState({
        is_active: user.is_active === 1,
        notifiche_realtime: user.notifiche_realtime === 1,
        is_permanent_supporter: user.is_permanent_supporter === 1,
        bacino: user.bacino || '',
        linee: user.linee ? user.linee.join(', ') : '',
        alarms: user.alarms ? user.alarms.join(', ') : ''
    });
    const [saving, setSaving] = useState(false);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const linesArray = formData.linee.split(',').map(s => s.trim()).filter(Boolean);
            const alarmsArray = formData.alarms.split(',').map(s => s.trim()).filter(Boolean);

            await onSave(user.user_id, {
                is_active: formData.is_active,
                notifiche_realtime: formData.notifiche_realtime,
                is_permanent_supporter: formData.is_permanent_supporter,
                bacino: formData.bacino,
                linee: linesArray,
                alarms: alarmsArray
            });
            onClose();
        } catch (err) {
            alert('Errore durante il salvataggio: ' + err.message);
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="glass-panel w-full max-w-lg rounded-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="p-5 border-b border-white/10 flex justify-between items-center">
                    <div>
                        <h2 className="text-xl font-bold text-white">Modifica Utente</h2>
                        <p className="text-sm text-gray-400 font-mono mt-1">ID: {user.user_id}</p>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <i className="fas fa-times text-xl"></i>
                    </button>
                </div>

                <div className="p-5 overflow-y-auto custom-scrollbar flex-1">
                    <form id="editForm" onSubmit={handleSubmit} className="space-y-4">

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                            <label className="flex items-center space-x-3 p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition">
                                <input type="checkbox" name="is_active" checked={formData.is_active} onChange={handleChange} className="w-5 h-5 rounded border-gray-600 text-primary focus:ring-primary focus:ring-offset-gray-900 bg-gray-800" />
                                <span className="text-sm font-medium">Utente Attivo</span>
                            </label>

                            <label className="flex items-center space-x-3 p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition">
                                <input type="checkbox" name="notifiche_realtime" checked={formData.notifiche_realtime} onChange={handleChange} className="w-5 h-5 rounded border-gray-600 text-primary focus:ring-primary focus:ring-offset-gray-900 bg-gray-800" />
                                <span className="text-sm font-medium">Notifiche Realtime</span>
                            </label>

                            <label className="flex items-center space-x-3 p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition sm:col-span-2">
                                <input type="checkbox" name="is_permanent_supporter" checked={formData.is_permanent_supporter} onChange={handleChange} className="w-5 h-5 rounded border-gray-600 text-yellow-500 focus:ring-yellow-500 focus:ring-offset-gray-900 bg-gray-800" />
                                <span className="text-sm font-medium text-yellow-400"><i className="fas fa-star mr-2"></i>Supporter Permanente</span>
                            </label>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Bacino</label>
                            <select name="bacino" value={formData.bacino} onChange={handleChange} className="w-full bg-gray-800 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-primary/50">
                                <option value="">Nessuno</option>
                                <option value="FC">Forlì-Cesena (FC)</option>
                                <option value="RA">Ravenna (RA)</option>
                                <option value="RN">Rimini (RN)</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Linee Monitorate (separate da virgola)</label>
                            <input type="text" name="linee" value={formData.linee} onChange={handleChange} placeholder="Es: 92, 94, 11" className="w-full bg-gray-800 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono" />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Allarmi Giornalieri (HH:MM separati da virgola)</label>
                            <input type="text" name="alarms" value={formData.alarms} onChange={handleChange} placeholder="Es: 07:30, 13:15" className="w-full bg-gray-800 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono" />
                        </div>

                    </form>
                </div>

                <div className="p-5 border-t border-white/10 bg-black/20 flex justify-end space-x-3">
                    <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-white/10 transition">
                        Annulla
                    </button>
                    <button type="submit" form="editForm" disabled={saving} className="px-5 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-blue-600 text-white shadow-lg shadow-primary/30 transition disabled:opacity-50 flex items-center">
                        {saving ? <i className="fas fa-spinner fa-spin mr-2"></i> : <i className="fas fa-save mr-2"></i>}
                        Salva Modifiche
                    </button>
                </div>
            </div>
        </div>
    );
}

function App() {
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [editingUser, setEditingUser] = useState(null);

    const loadData = async () => {
        try {
            const [statsData, usersData] = await Promise.all([
                api.getStats(),
                api.getUsers()
            ]);
            setStats(statsData);
            setUsers(usersData);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleSaveUser = async (id, data) => {
        await api.updateUser(id, data);
        await loadData(); // Reload all to update stats too
    };

    const handleDeleteUser = async (user) => {
        if (window.confirm(`Sei sicuro di voler eliminare l'utente ${user.user_id}? Questa azione eliminerà anche le sue linee e allarmi salvati.`)) {
            try {
                await api.deleteUser(user.user_id);
                await loadData();
            } catch (err) {
                alert('Errore eliminazione: ' + err.message);
            }
        }
    };

    const filteredUsers = useMemo(() => {
        if (!search) return users;
        const q = search.toLowerCase();
        return users.filter(u =>
            u.user_id.toString().includes(q) ||
            (u.bacino && u.bacino.toLowerCase().includes(q)) ||
            (u.linee && u.linee.join(' ').toLowerCase().includes(q))
        );
    }, [users, search]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-primary text-4xl animate-pulse"><i className="fas fa-bus"></i></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="glass-panel p-6 rounded-2xl max-w-md w-full text-center border-red-500/30">
                    <div className="w-16 h-16 rounded-full bg-red-500/20 text-red-500 flex items-center justify-center mx-auto mb-4 text-2xl">
                        <i className="fas fa-exclamation-triangle"></i>
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">Errore di Caricamento</h2>
                    <p className="text-gray-400 mb-6">{error}</p>
                    <button onClick={loadData} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition font-medium">
                        Riprova
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <header className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 animate-fade-in">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight flex items-center">
                        <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mr-3 shadow-lg">
                            <i className="fas fa-bus text-lg"></i>
                        </span>
                        BusBot Admin
                    </h1>
                    <p className="text-gray-400 mt-1 ml-13">Pannello di controllo locale</p>
                </div>
                <div className="mt-4 md:mt-0 glass-panel px-4 py-2 rounded-lg text-sm font-medium text-gray-300 flex items-center">
                    <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
                    API Online
                </div>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatCard title="Utenti Totali" value={stats.total_users} icon="users" color="blue" delay="" />
                <StatCard title="Utenti Attivi" value={stats.active_users} icon="check-circle" color="green" delay="delay-100" />
                <StatCard title="Notifiche Realtime" value={stats.realtime_users} icon="bolt" color="yellow" delay="delay-200" />
                <StatCard title="Supporter" value={stats.permanent_supporters} icon="star" color="purple" delay="delay-300" />
            </div>

            {/* Users Table */}
            <div className="glass-panel rounded-2xl overflow-hidden animate-fade-in delay-300 flex flex-col">
                <div className="p-5 border-b border-white/10 flex flex-col sm:flex-row justify-between items-center gap-4 bg-white/5">
                    <h2 className="text-lg font-bold text-white flex items-center">
                        <i className="fas fa-address-book mr-2 text-gray-400"></i> Gestione Utenti
                    </h2>
                    <div className="relative w-full sm:w-72">
                        <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500"></i>
                        <input
                            type="text"
                            placeholder="Cerca per ID, bacino, linea..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="w-full bg-black/30 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-black/20 text-gray-400 font-medium border-b border-white/5">
                            <tr>
                                <th className="px-6 py-4">ID Utente</th>
                                <th className="px-6 py-4">Stato</th>
                                <th className="px-6 py-4">Bacino</th>
                                <th className="px-6 py-4">Linee</th>
                                <th className="px-6 py-4">Allarmi</th>
                                <th className="px-6 py-4 text-right">Azioni</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredUsers.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="px-6 py-12 text-center text-gray-400">
                                        Nessun utente trovato.
                                    </td>
                                </tr>
                            ) : filteredUsers.map(user => (
                                <tr key={user.user_id} className="hover:bg-white/5 transition-colors group">
                                    <td className="px-6 py-4 font-mono text-gray-300">
                                        {user.user_id}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center space-x-2">
                                            {user.is_active ?
                                                <span className="w-2.5 h-2.5 rounded-full bg-green-500" title="Attivo"></span> :
                                                <span className="w-2.5 h-2.5 rounded-full bg-red-500" title="Disattivo"></span>
                                            }
                                            {user.notifiche_realtime === 1 && <i className="fas fa-bolt text-yellow-500 text-xs" title="Notifiche Realtime"></i>}
                                            {user.is_permanent_supporter === 1 && <i className="fas fa-star text-purple-400 text-xs" title="Supporter Permanente"></i>}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 font-medium text-gray-200">
                                        {user.bacino || <span className="text-gray-600">—</span>}
                                    </td>
                                    <td className="px-6 py-4 text-gray-400 max-w-[200px] truncate" title={user.linee?.join(', ')}>
                                        {user.linee?.length > 0 ? (
                                            <div className="flex flex-wrap gap-1">
                                                {user.linee.slice(0, 3).map(l => (
                                                    <span key={l} className="bg-white/10 px-2 py-0.5 rounded text-xs">{l}</span>
                                                ))}
                                                {user.linee.length > 3 && <span className="text-xs ml-1">+{user.linee.length - 3}</span>}
                                            </div>
                                        ) : <span className="text-gray-600">—</span>}
                                    </td>
                                    <td className="px-6 py-4 text-gray-400 font-mono text-xs">
                                        {user.alarms?.length > 0 ? user.alarms.join(', ') : <span className="text-gray-600">—</span>}
                                    </td>
                                    <td className="px-6 py-4 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => setEditingUser(user)}
                                            className="w-8 h-8 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white transition flex items-center justify-center mr-2 inline-flex"
                                            title="Modifica"
                                        >
                                            <i className="fas fa-edit"></i>
                                        </button>
                                        <button
                                            onClick={() => handleDeleteUser(user)}
                                            className="w-8 h-8 rounded bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white transition flex items-center justify-center inline-flex"
                                            title="Elimina"
                                        >
                                            <i className="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div className="p-4 bg-black/20 text-xs border-t border-white/5 text-gray-500 text-right">
                    Mostrando {filteredUsers.length} utenti
                </div>
            </div>

            {/* Edit Modal */}
            {editingUser && (
                <UserModal
                    user={editingUser}
                    onClose={() => setEditingUser(null)}
                    onSave={handleSaveUser}
                />
            )}
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
