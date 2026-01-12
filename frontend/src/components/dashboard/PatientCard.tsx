import { Patient } from '@/lib/api';
import { ChevronRight, Heart, Activity } from 'lucide-react';

interface PatientCardProps {
  patient: Patient;
  onClick: () => void;
  index: number;
}

const sentimentColors = {
  amazing: 'bg-emerald-500',
  good: 'bg-green-400',
  neutral: 'bg-yellow-400',
  poor: 'bg-orange-400',
  terrible: 'bg-red-500',
};

export function PatientCard({ patient, onClick, index }: PatientCardProps) {
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
          <div className="hidden sm:flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Heart className="h-4 w-4 text-primary" />
              <span>{avgHeartRate} bpm</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${sentimentColors[patient.sentiment]}`} />
              <span className="capitalize">{patient.sentiment}</span>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
        </div>
      </div>
    </button>
  );
}
