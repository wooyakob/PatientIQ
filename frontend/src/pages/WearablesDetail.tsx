import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, Heart, Footprints, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { getPatient } from '@/lib/api';

const WearablesDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';

  const {
    data: patient,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => getPatient(patientId),
    enabled: Boolean(patientId),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading wearable data…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load wearable data</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Patient not found</h1>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const heartRates = patient.wearableData.heartRate ?? [];
  const stepCounts = patient.wearableData.stepCount ?? [];
  const avgHeartRate = Math.round(heartRates.reduce((a, b) => a + b, 0) / (heartRates.length || 1));
  const avgSteps = Math.round(stepCounts.reduce((a, b) => a + b, 0) / (stepCounts.length || 1));
  const maxHeartRate = heartRates.length ? Math.max(...heartRates) : 0;
  const minHeartRate = heartRates.length ? Math.min(...heartRates) : 0;
  const maxSteps = stepCounts.length ? Math.max(...stepCounts) : 0;

  const heartRateTrend = heartRates.length >= 2 ? heartRates[heartRates.length - 1] - heartRates[0] : 0;
  const stepsTrend = stepCounts.length >= 2 ? stepCounts[stepCounts.length - 1] - stepCounts[0] : 0;

  const getTrendIcon = (trend: number) => {
    if (trend > 2) return <TrendingUp className="h-4 w-4 text-emerald-500" />;
    if (trend < -2) return <TrendingDown className="h-4 w-4 text-primary" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-4xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate(`/patient/${patient.id}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to {patient.name}</span>
        </button>

        <div className="glass-card p-8 mb-6 animate-slide-up">
          <div className="flex items-center gap-4 mb-6">
            <div className="neo-card p-3 rounded-xl">
              <Heart className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Wearable Data Analysis</h1>
              <p className="text-muted-foreground">7-day overview for {patient.name}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="neo-card p-4 rounded-xl">
              <p className="text-xs text-muted-foreground mb-1">Avg Heart Rate</p>
              <p className="text-2xl font-bold text-foreground">{avgHeartRate}</p>
              <p className="text-xs text-muted-foreground">bpm</p>
            </div>
            <div className="neo-card p-4 rounded-xl">
              <p className="text-xs text-muted-foreground mb-1">HR Range</p>
              <p className="text-2xl font-bold text-foreground">{minHeartRate}-{maxHeartRate}</p>
              <p className="text-xs text-muted-foreground">bpm</p>
            </div>
            <div className="neo-card p-4 rounded-xl">
              <p className="text-xs text-muted-foreground mb-1">Avg Steps</p>
              <p className="text-2xl font-bold text-foreground">{avgSteps.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">daily</p>
            </div>
            <div className="neo-card p-4 rounded-xl">
              <p className="text-xs text-muted-foreground mb-1">Best Day</p>
              <p className="text-2xl font-bold text-foreground">{maxSteps.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">steps</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Heart className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">Heart Rate</h3>
              </div>
              <div className="flex items-center gap-1">
                {getTrendIcon(heartRateTrend)}
                <span className="text-xs text-muted-foreground">7d trend</span>
              </div>
            </div>
            <div className="space-y-3">
              {heartRates.slice(0, 7).map((rate, index) => (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-8">{days[index]}</span>
                  <div className="flex-1 neo-inset h-6 rounded-full overflow-hidden">
                    <div 
                      className="h-full gradient-primary rounded-full transition-all duration-500"
                      style={{ width: `${(rate / 100) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-foreground w-12">{rate} bpm</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: '150ms' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Footprints className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">Step Count</h3>
              </div>
              <div className="flex items-center gap-1">
                {getTrendIcon(stepsTrend)}
                <span className="text-xs text-muted-foreground">7d trend</span>
              </div>
            </div>
            <div className="space-y-3">
              {stepCounts.slice(0, 7).map((steps, index) => (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-8">{days[index]}</span>
                  <div className="flex-1 neo-inset h-6 rounded-full overflow-hidden">
                    <div 
                      className="h-full gradient-primary rounded-full transition-all duration-500"
                      style={{ width: `${(steps / 10000) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-foreground w-16">{steps.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default WearablesDetail;
