import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, FileText, Calendar, Clock, Plus, Edit2, X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDateOnlyForDisplay, getPatientWithNotes, saveDoctorNote, deleteDoctorNote, toLocalDateOnlyString } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const NotesDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    data: patient,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patient', patientId, 'notes'],
    queryFn: () => getPatientWithNotes(patientId),
    enabled: Boolean(patientId),
  });

  const [showNewNote, setShowNewNote] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editNoteContent, setEditNoteContent] = useState('');

  const saveMutation = useMutation({
    mutationFn: saveDoctorNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'notes'] });
      toast({
        title: 'Success',
        description: 'Doctor note saved successfully',
      });
      setNewNoteContent('');
      setShowNewNote(false);
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to save doctor note',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDoctorNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'notes'] });
      toast({
        title: 'Success',
        description: 'Doctor note deleted successfully',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete doctor note',
        variant: 'destructive',
      });
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading notes…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load notes</h1>
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

  const handleAddNote = () => {
    if (!newNoteContent.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter note content',
        variant: 'destructive',
      });
      return;
    }

    const noteData = {
      visit_date: toLocalDateOnlyString(new Date()),
      doctor_name: 'Tiffany Mitchell',
      doctor_id: '1',
      visit_notes: newNoteContent.trim(),
      patient_name: patient.name,
      patient_id: patientId,
    };

    saveMutation.mutate(noteData);
  };

  const handleEditNote = (note: any) => {
    setEditingNoteId(note.id);
    setEditNoteContent(note.content);
  };

  const handleSaveEdit = () => {
    if (!editNoteContent.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter note content',
        variant: 'destructive',
      });
      return;
    }

    const noteToEdit = patient?.doctorNotes.find(n => n.id === editingNoteId);
    if (!noteToEdit) {
      toast({
        title: 'Error',
        description: 'Note not found',
        variant: 'destructive',
      });
      return;
    }

    const noteData = {
      visit_date: noteToEdit.date,
      doctor_name: 'Tiffany Mitchell',
      doctor_id: '1',
      visit_notes: editNoteContent.trim(),
      patient_name: patient?.name || '',
      patient_id: patientId,
    };

    saveMutation.mutate(noteData, {
      onSuccess: () => {
        setEditingNoteId(null);
        setEditNoteContent('');
      }
    });
  };

  const handleCancelEdit = () => {
    setEditingNoteId(null);
    setEditNoteContent('');
  };

  const handleDeleteNote = (noteId: string) => {
    if (confirm('Are you sure you want to delete this note? This action cannot be undone.')) {
      deleteMutation.mutate(noteId);
    }
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
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="neo-card p-3 rounded-xl">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Doctor's Notes</h1>
                <p className="text-muted-foreground">Clinical notes for {patient.name}</p>
              </div>
            </div>
            <Button onClick={() => setShowNewNote(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Note
            </Button>
          </div>

          {showNewNote && (
            <div className="neo-card p-5 rounded-xl mb-6 animate-scale-in">
              <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                </span>
              </div>
              <textarea
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Enter your clinical notes here..."
                className="w-full h-32 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none resize-none text-sm leading-relaxed"
              />
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-border">
                <Button variant="ghost" onClick={() => setShowNewNote(false)}>Cancel</Button>
                <Button onClick={handleAddNote} disabled={saveMutation.isPending}>
                  {saveMutation.isPending ? 'Saving...' : 'Save Note'}
                </Button>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {patient.doctorNotes.map((note, index) => (
              <div
                key={note.id}
                className="neo-card p-5 rounded-xl animate-slide-up"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {editingNoteId === note.id ? (
                  <>
                    <div className="flex items-center gap-4 mb-3 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        {formatDateOnlyForDisplay(note.date)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {note.time}
                      </span>
                    </div>
                    <textarea
                      value={editNoteContent}
                      onChange={(e) => setEditNoteContent(e.target.value)}
                      placeholder="Enter your clinical notes here..."
                      className="w-full h-32 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none resize-none text-sm leading-relaxed mb-3"
                    />
                    <div className="flex justify-end gap-3 pt-3 border-t border-border">
                      <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                      </Button>
                      <Button size="sm" onClick={handleSaveEdit} disabled={saveMutation.isPending}>
                        {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5" />
                          {formatDateOnlyForDisplay(note.date)}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          {note.time}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditNote(note)}
                          className="h-8"
                        >
                          <Edit2 className="h-3.5 w-3.5 mr-1.5" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteNote(note.id)}
                          className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                          Delete
                        </Button>
                      </div>
                    </div>
                    <p className="text-foreground leading-relaxed">{note.content}</p>
                  </>
                )}
              </div>
            ))}
          </div>

          {patient.doctorNotes.length === 0 && !showNewNote && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No clinical notes recorded yet.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default NotesDetail;
