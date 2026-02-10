import { createContext, useContext, useState, ReactNode } from 'react';

export interface Provider {
    id: string;
    name: string;
    role: 'provider' | 'admin';
}

interface AuthContextType {
    user: Provider | null;
    login: (providerId: string) => void;
    logout: () => void;
    providers: Provider[];
}

const MOCK_PROVIDERS: Provider[] = [
    { id: 'provider-1', name: 'Dr. Sarah Smith', role: 'provider' },
    { id: 'provider-2', name: 'Dr. James Jones', role: 'provider' },
    { id: 'admin', name: 'Practice Admin', role: 'admin' },
];

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    // Default to first provider for verified E2E flow
    const [user, setUser] = useState<Provider | null>(MOCK_PROVIDERS[0]);

    const login = (providerId: string) => {
        const provider = MOCK_PROVIDERS.find(p => p.id === providerId);
        if (provider) {
            setUser(provider);
        }
    };

    const logout = () => {
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, providers: MOCK_PROVIDERS }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
