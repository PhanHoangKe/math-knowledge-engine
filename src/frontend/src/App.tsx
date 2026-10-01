import React from 'react';
import { PreferencesProvider } from './state/preferences';
import { AppShell } from './components/AppShell/AppShell';

export const App: React.FC = () => {
  return (
    <PreferencesProvider>
      <AppShell />
    </PreferencesProvider>
  );
};

export default App;
