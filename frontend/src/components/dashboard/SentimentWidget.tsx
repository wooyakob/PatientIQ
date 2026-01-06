import { Patient } from '@/lib/api';
import { Smile, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface SentimentWidgetProps {
  patient: Patient;
}

const sentimentConfig = {
  amazing: { color: 'bg-emerald-500', position: '90%', label: 'Amazing' },
  good: { color: 'bg-green-400', position: '70%', label: 'Good' },
  neutral: { color: 'bg-yellow-400', position: '50%', label: 'Neutral' },
  poor: { color: 'bg-orange-400', position: '30%', label: 'Poor' },
  terrible: { color: 'bg-red-500', position: '10%', label: 'Terrible' },
};

export function SentimentWidget({ patient }: SentimentWidgetProps) {
  const config = sentimentConfig[patient.sentiment];

  return (
    <Link
      to={`/patient/${patient.id}/sentiment`}
      className="glass-card p-6 block transition-all duration-300 hover:scale-[1.01] hover:shadow-xl group"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="neo-card p-2.5 rounded-xl">
            <Smile className="h-5 w-5 text-primary" />
          </div>
          <h3 className="font-semibold text-foreground">Patient Sentiment</h3>
        </div>
        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-xs text-muted-foreground mb-2">
          <span>Terrible</span>
          <span>Amazing</span>
        </div>
        <div className="neo-inset h-3 rounded-full relative overflow-hidden">
          <div 
            className="absolute h-full rounded-full bg-gradient-to-r from-red-500 via-yellow-400 to-emerald-500 opacity-30"
            style={{ width: '100%' }}
          />
          <div 
            className={`absolute top-1/2 -translate-y-1/2 h-5 w-5 rounded-full ${config.color} shadow-lg border-2 border-card transition-all duration-500`}
            style={{ left: config.position, transform: 'translate(-50%, -50%)' }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${config.color} text-card`}>
          {config.label}
        </span>
        <span className="text-xs text-muted-foreground">Based on patient notes</span>
      </div>
    </Link>
  );
}
