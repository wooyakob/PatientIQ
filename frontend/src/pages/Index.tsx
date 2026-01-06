import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { PatientCard } from '@/components/dashboard/PatientCard';
import { Users, Search } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPatients } from '@/lib/api';

const Index = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data: patients = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patients'],
    queryFn: getPatients,
  });

  const filteredPatients = patients.filter(patient =>
    patient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    patient.condition.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <div className="neo-card p-2.5 rounded-xl">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">Patient Overview</h1>
          </div>
          <p className="text-muted-foreground">Select a patient to view their 360° health profile</p>
        </div>

        <div className="glass-card p-4 mb-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search patients by name or condition..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none text-sm"
            />
          </div>
        </div>

        {isLoading && (
          <div className="glass-card p-12 text-center animate-fade-in">
            <p className="text-muted-foreground">Loading patients…</p>
          </div>
        )}

        {isError && (
          <div className="glass-card p-12 text-center animate-fade-in">
            <p className="text-muted-foreground">
              Failed to load patients: {(error as Error).message}
            </p>
          </div>
        )}

        {!isLoading && !isError && (
          <div className="space-y-3">
            {filteredPatients.map((patient, index) => (
              <PatientCard
                key={patient.id}
                patient={patient}
                onClick={() => navigate(`/patient/${patient.id}`)}
                index={index}
              />
            ))}
          </div>
        )}

        {filteredPatients.length === 0 && (
          <div className="glass-card p-12 text-center animate-fade-in">
            <p className="text-muted-foreground">No patients found matching your search.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
