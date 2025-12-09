'use client';

import { useEffect, useRef } from 'react';

interface DrawerProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
    side?: 'left' | 'right';
}

/**
 * Slide-out drawer panel component
 */
export function Drawer({ isOpen, onClose, title, children, side = 'right' }: DrawerProps) {
    const drawerRef = useRef<HTMLDivElement>(null);

    // Handle escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) onClose();
        };
        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    // Handle click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (drawerRef.current && !drawerRef.current.contains(e.target as Node) && isOpen) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isOpen, onClose]);

    // Prevent body scroll when open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    const sideStyles = side === 'left'
        ? { left: 0, transform: isOpen ? 'translateX(0)' : 'translateX(-100%)' }
        : { right: 0, transform: isOpen ? 'translateX(0)' : 'translateX(100%)' };

    return (
        <>
            {/* Backdrop */}
            <div
                className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
                    }`}
                aria-hidden="true"
            />

            {/* Drawer */}
            <div
                ref={drawerRef}
                className="fixed top-0 bottom-0 w-80 max-w-[85vw] bg-card border-border z-50 flex flex-col transition-transform duration-200 ease-out"
                style={{
                    ...sideStyles,
                    borderLeft: side === 'right' ? '1px solid var(--border)' : undefined,
                    borderRight: side === 'left' ? '1px solid var(--border)' : undefined,
                }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                    <h2 className="text-sm font-semibold">{title}</h2>
                    <button
                        onClick={onClose}
                        className="btn-ghost p-1.5 rounded hover:bg-secondary"
                        aria-label="Cerrar"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {children}
                </div>
            </div>
        </>
    );
}
