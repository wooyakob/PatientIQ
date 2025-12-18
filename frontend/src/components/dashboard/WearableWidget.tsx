import { Patient } from '@/data/mockPatients';
import { Heart, Footprints, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface WearableWidgetProps {
  patient: Patient;
}

export function WearableWidget({ patient }: WearableWidgetProps) {
  const avgHeartRate = Math.round(
    patient.wearableData.heartRate.reduce((a, b) => a + b, 0) / 7
  );
  const avgSteps = Math.round(
    patient.wearableData.stepCount.reduce((a, b) => a + b, 0) / 7
  );

  const heartRateMin = Math.min(...patient.wearableData.heartRate);
  const heartRateMax = Math.max(...patient.wearableData.heartRate);

  return (
    <Link
      to={`/patient/${patient.id}/wearables`}
      className="glass-card p-6 block transition-all duration-300 hover:scale-[1.01] hover:shadow-xl group"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="neo-card p-2.5 rounded-xl">
            <Heart className="h-5 w-5 text-primary" />
          </div>
          <h3 className="font-semibold text-foreground">Wearable Data</h3>
        </div>
        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      
      <p className="text-xs text-muted-foreground mb-4">7-Day Averages</p>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="neo-inset rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Heart className="h-4 w-4 text-primary" />
            <span className="text-xs text-muted-foreground">Heart Rate</span>
          </div>
          <p className="text-2xl font-bold text-foreground">{avgHeartRate}</p>
          <p className="text-xs text-muted-foreground">bpm avg</p>
          <p className="text-xs text-muted-foreground mt-1">
            Range: {heartRateMin}-{heartRateMax}
          </p>
        </div>
        
        <div className="neo-inset rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Footprints className="h-4 w-4 text-primary" />
            <span className="text-xs text-muted-foreground">Steps</span>
          </div>
          <p className="text-2xl font-bold text-foreground">{avgSteps.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">daily avg</p>
        </div>
      </div>
    </Link>
  );
}
