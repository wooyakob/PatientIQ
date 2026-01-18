import { Patient } from '@/lib/api';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Heart, Activity } from 'lucide-react';

interface PatientCardProps {
  patient: Patient;
  onClick: () => void;
  index: number;
}

const sentimentColors = {
  positive: 'bg-emerald-500',
  neutral: 'bg-yellow-400',
  mixed: 'bg-orange-400',
  negative: 'bg-red-500',
};

export function PatientCard({ patient, onClick, index }: PatientCardProps) {
  const navigate = useNavigate();
  const sentimentLabel = String(patient.sentiment ?? '').trim();
  const avgHeartRate = Math.round(
    patient.wearableData.heartRate.reduce((a, b) => a + b, 0) /
      (patient.wearableData.heartRate.length || 1)
  );

  return (
    <button
      onClick={onClick}
      className="glass-card w-full p-5 text-left transition-all duration-300 hover:scale-[1.02] hover:shadow-xl animate-slide-up group"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="neo-card h-12 w-12 flex items-center justify-center rounded-full text-sm font-semibold text-primary">
            {patient.avatar}
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{patient.name}</h3>
            <p className="text-sm text-muted-foreground">{patient.condition}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              navigate(`/patient/${patient.id}/summary`);
            }}
            className="hidden sm:inline-flex items-center rounded-md border border-border/60 bg-background/40 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-background/70 transition-colors"
          >
            Summary
          </button>
          <div className="hidden sm:flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Heart className="h-4 w-4 text-primary" />
              <span>{avgHeartRate} bpm</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${sentimentColors[patient.sentiment]}`} />
              <span className="capitalize">{sentimentLabel}</span>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
        </div>
      </div>
    </button>
  );
}
