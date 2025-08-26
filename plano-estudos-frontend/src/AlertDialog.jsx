import React from 'react';
import { Modal, Button } from './components';
import { AlertTriangle } from 'lucide-react';

export function AlertDialog({ isOpen, onClose, title, message, confirmLabel = 'OK', cancelLabel, onConfirm, type = 'alert' }) {
    return (
        <Modal isOpen={isOpen} onClose={onClose} title={title}>
            <div className="alert-dialog">
                <div className="alert-dialog-content">
                    {type === 'error' && (
                        <div className="alert-dialog-icon error">
                            <AlertTriangle size={24} />
                        </div>
                    )}
                    <p className="alert-dialog-message">{message}</p>
                </div>
                <div className="alert-dialog-actions">
                    {cancelLabel && (
                        <Button variant="ghost" onClick={onClose}>
                            {cancelLabel}
                        </Button>
                    )}
                    <Button 
                        variant={type === 'error' ? 'danger' : 'primary'} 
                        onClick={() => {
                            onConfirm?.();
                            onClose();
                        }}
                    >
                        {confirmLabel}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
