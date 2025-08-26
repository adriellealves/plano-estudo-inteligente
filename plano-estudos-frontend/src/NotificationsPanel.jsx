// src/NotificationsPanel.jsx
import React, { useState, useEffect, useRef } from 'react';
import { api } from './api';
import { Bell, X, Check, AlertTriangle, Target, Calendar, Trophy } from 'lucide-react';
import { Button } from './components';
import { useOnClickOutside } from './hooks';

export function NotificationsPanel() {
    const [notifications, setNotifications] = useState([]);
    const [showPanel, setShowPanel] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const panelRef = useRef(null);

    useOnClickOutside(panelRef, () => setShowPanel(false));

    useEffect(() => {
        loadNotifications();
        // Recarrega notificações a cada 5 minutos
        const interval = setInterval(loadNotifications, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const loadNotifications = async () => {
        try {
            setLoading(true);
            const data = await api('/notifications');
            setNotifications(data);
            setUnreadCount(data.filter(n => !n.read).length);
            setLoading(false);
        } catch (e) {
            console.error('Erro ao carregar notificações:', e);
            setLoading(false);
        }
    };

    const handleMarkAsRead = async (ids) => {
        try {
            await api('/notifications/mark-read', {
                method: 'POST',
                body: JSON.stringify({ ids })
            });
            await loadNotifications();
        } catch (e) {
            console.error('Erro ao marcar notificações como lidas:', e);
        }
    };

    const getNotificationIcon = (type) => {
        switch (type) {
            case 'goal':
                return <Target size={20} className="notification-icon" />;
            case 'review':
                return <Calendar size={20} className="notification-icon" />;
            case 'performance':
                return <AlertTriangle size={20} className="notification-icon" />;
            case 'achievement':
                return <Trophy size={20} className="notification-icon" />;
            default:
                return <Bell size={20} className="notification-icon" />;
        }
    };

    const getNotificationBorderColor = (type, priority) => {
        if (priority === 'high') return 'var(--error-color)';
        
        switch (type) {
            case 'goal':
                return '#10b981'; // Verde
            case 'achievement':
                return '#f59e0b'; // Laranja
            case 'performance':
                return '#ef4444'; // Vermelho
            case 'review':
                return '#3b82f6'; // Azul
            default:
                return 'var(--primary-color)';
        }
    };

    function formatTimeAgo(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d atrás`;
        if (hours > 0) return `${hours}h atrás`;
        if (minutes > 0) return `${minutes}m atrás`;
        return 'Agora';
    }

    return (
        <div className="notifications-container">
            <Button
                variant="ghost"
                onClick={() => setShowPanel(!showPanel)}
                className="notifications-trigger"
            >
                <Bell size={20} />
                {unreadCount > 0 && (
                    <span className="notifications-badge">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
            </Button>

            {showPanel && (
                <div className="notifications-panel" ref={panelRef}>
                    <div className="notifications-header">
                        <h3>Notificações</h3>
                        <Button
                            variant="ghost"
                            onClick={() => setShowPanel(false)}
                            className="notification-action"
                        >
                            <X size={16} />
                        </Button>
                    </div>

                    {loading ? (
                        <div className="notifications-empty">
                            Carregando notificações...
                        </div>
                    ) : notifications.length === 0 ? (
                        <div className="notifications-empty">
                            Nenhuma notificação pendente
                        </div>
                    ) : (
                        <>
                            <div className="notifications-list">
                                {notifications.map(notification => (
                                    <div
                                        key={notification.id}
                                        className="notification-item"
                                        style={{
                                            borderLeftColor: getNotificationBorderColor(notification.type, notification.priority),
                                            backgroundColor: notification.read ? 'inherit' : '#f9fafb'
                                        }}
                                    >
                                        {getNotificationIcon(notification.type)}
                                        <div className="notification-content">
                                            <div className="notification-title">
                                                {notification.title}
                                            </div>
                                            <div className="notification-message">
                                                {notification.message}
                                            </div>
                                            <div className="notification-time">
                                                {formatTimeAgo(notification.created_at)}
                                            </div>
                                        </div>
                                        {!notification.read && (
                                            <Button
                                                variant="ghost"
                                                onClick={() => handleMarkAsRead([notification.id])}
                                                className="notification-action"
                                                title="Marcar como lida"
                                            >
                                                <Check size={16} />
                                            </Button>
                                        )}
                                    </div>
                                ))}
                            </div>
                            {notifications.some(n => !n.read) && (
                                <div className="notifications-footer">
                                    <Button
                                        onClick={() => handleMarkAsRead(
                                            notifications.filter(n => !n.read).map(n => n.id)
                                        )}
                                    >
                                        Marcar todas como lidas
                                    </Button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
