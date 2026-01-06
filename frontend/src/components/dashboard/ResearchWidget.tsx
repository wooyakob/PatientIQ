import { Patient } from '@/lib/api';
import { BookOpen, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ResearchWidgetProps {
  patient: Patient;
}

export function ResearchWidget({ patient }: ResearchWidgetProps) {
  return (
    <Link
      to={`/patient/${patient.id}/research`}
      className="glass-card p-6 block transition-all duration-300 hover:scale-[1.01] hover:shadow-xl group"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="neo-card p-2.5 rounded-xl">
            <BookOpen className="h-5 w-5 text-primary" />
          </div>
          <h3 className="font-semibold text-foreground">Medical Research</h3>
        </div>
        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      <p className="text-sm font-medium text-primary mb-3">{patient.researchTopic}</p>
      <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
        {patient.researchContent[0]}
      </p>
    </Link>
  );
}
