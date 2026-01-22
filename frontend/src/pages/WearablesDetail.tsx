import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, Heart, Footprints, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { getPatient, getPatientWearables, getPatientWearablesSummary } from '@/lib/api';

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

  const {
    data: wearables,
    isLoading: isWearablesLoading,
    isError: isWearablesError,
    error: wearablesError,
  } = useQuery({
    queryKey: ['patient-wearables', patientId, 30],
    queryFn: () => getPatientWearables(patientId, 30),
    enabled: Boolean(patientId),
  });

  const {
    data: wearablesSummary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
  } = useQuery({
    queryKey: ['patient-wearables-summary', patientId, 30],
    queryFn: () => getPatientWearablesSummary(patientId, 30),
    enabled: Boolean(patientId),
    staleTime: 1000 * 60 * 60,
  });

  if (isLoading || isWearablesLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading wearable data…</p>
        </div>
      </div>
    );
  }

  if (isError || isWearablesError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load wearable data</h1>
          <p className="text-muted-foreground mb-6">{((error ?? wearablesError) as Error).message}</p>
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

  const formatTimestampLabel = (ts: string, fallback: string) => {
    const d = new Date(ts);
    return Number.isNaN(d.getTime())
      ? fallback
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const timestamps = wearables?.timestamps ?? [];
  const heartRates = wearables?.heartRate ?? [];
  const stepCounts = wearables?.stepCount ?? [];

  const availablePoints = Math.min(heartRates.length, stepCounts.length, timestamps.length);
  const pointsToShow = Math.min(30, availablePoints);

  const timestampsToShow = timestamps.slice(-pointsToShow);
  const heartRatesToShow = heartRates.slice(-pointsToShow);
  const stepCountsToShow = stepCounts.slice(-pointsToShow);

  const timestampsNewestFirst = [...timestampsToShow].reverse();
  const heartRatesNewestFirst = [...heartRatesToShow].reverse();
  const stepCountsNewestFirst = [...stepCountsToShow].reverse();

  const avgHeartRate = Math.round(heartRates.reduce((a, b) => a + b, 0) / (heartRates.length || 1));
  const avgSteps = Math.round(stepCounts.reduce((a, b) => a + b, 0) / (stepCounts.length || 1));
  const maxHeartRate = heartRates.length ? Math.max(...heartRates) : 0;
  const minHeartRate = heartRates.length ? Math.min(...heartRates) : 0;
  const maxSteps = stepCounts.length ? Math.max(...stepCounts) : 0;

  const heartRateTrend = heartRates.length >= 2 ? heartRates[heartRates.length - 1] - heartRates[0] : 0;
  const stepsTrend = stepCounts.length >= 2 ? stepCounts[stepCounts.length - 1] - stepCounts[0] : 0;

  const heartRateScaleMax = Math.max(maxHeartRate, 1);
  const stepScaleMax = Math.max(maxSteps, 1);

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
              <p className="text-muted-foreground">30-day overview for {patient.name}</p>
            </div>
          </div>

          <div className="neo-card p-5 rounded-2xl mb-6">
            <p className="text-xs text-muted-foreground mb-2">30-day summary</p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {isSummaryLoading
                ? 'Generating summary…'
                : isSummaryError
                  ? 'Unable to generate summary right now.'
                  : (wearablesSummary?.summary ?? '')}
            </p>
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
                <span className="text-xs text-muted-foreground">30d trend</span>
              </div>
            </div>
            <div className="space-y-3">
              {heartRatesNewestFirst.map((rate, index) => {
                const ts = timestampsNewestFirst[index] ?? '';
                return (
                  <div key={index} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-16">
                      {formatTimestampLabel(ts ?? '', `Day ${index + 1}`)}
                    </span>
                    <div className="flex-1 neo-inset h-6 rounded-full overflow-hidden">
                      <div 
                        className="h-full gradient-primary rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, (rate / heartRateScaleMax) * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-foreground w-12">{rate} bpm</span>
                  </div>
                );
              })}
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
                <span className="text-xs text-muted-foreground">30d trend</span>
              </div>
            </div>
            <div className="space-y-3">
              {stepCountsNewestFirst.map((steps, index) => {
                const ts = timestampsNewestFirst[index] ?? '';
                return (
                  <div key={index} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-16">
                      {formatTimestampLabel(ts ?? '', `Day ${index + 1}`)}
                    </span>
                    <div className="flex-1 neo-inset h-6 rounded-full overflow-hidden">
                      <div 
                        className="h-full gradient-primary rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, (steps / stepScaleMax) * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-foreground w-16">{steps.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default WearablesDetail;
