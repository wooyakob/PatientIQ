import { Header } from '@/components/Header';
import { useState } from 'react';
import { MessageSquare, Pin, Send, User, Search, PinOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPrivateMessages, getPublicMessages, sendPrivateMessage, sendPublicMessage, ApiStaffMessage } from '@/lib/api';

interface StaffMember {
  id: string;
  name: string;
  role: string;
  avatar: string;
  status: 'online' | 'away' | 'offline';
}

interface Message {
  id: string;
  senderId: string;
  senderName: string;
  recipientName?: string;
  subject: string;
  content: string;
  timestamp: string;
  isPinned: boolean;
  isPrivate: boolean;
  recipientId?: string;
  read?: boolean;
  priority?: string;
}

const mockStaff: StaffMember[] = [
  { id: 'admin_1', name: 'Medical Records', role: 'Administration', avatar: 'MR', status: 'online' },
  { id: 'admin_2', name: 'Appointment Desk', role: 'Scheduling', avatar: 'AD', status: 'online' },
  { id: 'pharmacy_1', name: 'Scripps Pharmacy', role: 'Pharmacy', avatar: 'SP', status: 'away' },
  { id: 'nurse_1', name: 'Sarah Johnson, RN', role: 'Nursing', avatar: 'SJ', status: 'online' },
  { id: 'radiologist_1', name: 'Dr. Michael Chen, Radiology', role: 'Radiology', avatar: 'RC', status: 'online' },
  { id: 'insurance_1', name: 'Insurance Verification', role: 'Insurance', avatar: 'IV', status: 'away' },
  { id: 'lab_1', name: 'Clinical Lab', role: 'Laboratory', avatar: 'CL', status: 'online' },
  { id: 'hr_dept', name: 'Human Resources', role: 'HR', avatar: 'HR', status: 'offline' },
  { id: 'quality_dept', name: 'Quality Assurance', role: 'Quality', avatar: 'QA', status: 'online' },
];

const currentDoctorId = '1';
const currentDoctorName = 'Tiffany Mitchell';

export default function Messages() {
  const queryClient = useQueryClient();

  const [selectedStaff, setSelectedStaff] = useState<StaffMember | null>(null);
  const [newSubject, setNewSubject] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'private'>('all');

  const [pinnedIds, setPinnedIds] = useState<Record<string, boolean>>({});

  const { data: privateMessages } = useQuery({
    queryKey: ['messages', 'private', currentDoctorId],
    queryFn: () => getPrivateMessages(currentDoctorId, 100),
  });

  const { data: publicMessages } = useQuery({
    queryKey: ['messages', 'public'],
    queryFn: () => getPublicMessages(100),
  });

  const sendPrivateMutation = useMutation({
    mutationFn: sendPrivateMessage,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['messages', 'private', currentDoctorId] });
      setNewSubject('');
      setNewMessage('');
      setSelectedStaff(null);
    },
  });

  const sendPublicMutation = useMutation({
    mutationFn: sendPublicMessage,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['messages', 'public'] });
      setNewSubject('');
      setNewMessage('');
      setSelectedStaff(null);
    },
  });

  const filteredStaff = mockStaff.filter(staff =>
    staff.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    staff.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toUiMessage = (m: ApiStaffMessage): Message => {
    const isPrivate = m.message_type === 'private';
    return {
      id: m.id,
      senderId: m.from_id,
      senderName: m.from_name,
      recipientName: isPrivate ? m.to_name : undefined,
      subject: m.subject,
      content: m.content,
      timestamp: m.timestamp,
      isPinned: !isPrivate && Boolean(pinnedIds[m.id]),
      isPrivate,
      recipientId: isPrivate ? m.to_id : undefined,
      read: m.read,
      priority: m.priority,
    };
  };

  const getPrivateDirectionLabel = (message: Message): string => {
    if (!message.isPrivate) return '';

    const isSent = message.senderId === currentDoctorId;
    const counterparty = isSent
      ? (message.recipientName ?? 'recipient')
      : (message.senderName ?? 'sender');

    return isSent ? `Sent (to ${counterparty})` : `Received (from ${counterparty})`;
  };

  const publicUiMessages: Message[] = (publicMessages ?? [])
    .map(toUiMessage)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const privateUiMessages: Message[] = (privateMessages ?? [])
    .map(toUiMessage)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const pinnedMessages = publicUiMessages.filter((m) => m.isPinned);
  const regularMessages = (activeTab === 'private' ? privateUiMessages : publicUiMessages).filter(
    (m) => !m.isPinned
  );

  const handleSendMessage = () => {
    if (!newSubject.trim() || !newMessage.trim()) return;

    if (selectedStaff) {
      sendPrivateMutation.mutate({
        to_id: selectedStaff.id,
        to_name: selectedStaff.name,
        subject: newSubject.trim(),
        content: newMessage.trim(),
      });
      return;
    }

    sendPublicMutation.mutate({
      subject: newSubject.trim(),
      content: newMessage.trim(),
    });
  };

  const togglePin = (messageId: string) => {
    setPinnedIds((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="gradient-primary p-2 rounded-xl">
              <MessageSquare className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-semibold text-foreground">Staff Messages</h1>
          </div>
          <p className="text-muted-foreground ml-12">Communicate with healthcare professionals</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Staff Directory */}
          <div className="glass-card neo-shadow rounded-2xl p-5">
            <h2 className="font-medium text-foreground mb-4">Medical Staff</h2>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search staff..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-muted/50 border-border/50"
              />
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {filteredStaff.map((staff) => (
                <button
                  key={staff.id}
                  onClick={() => setSelectedStaff(selectedStaff?.id === staff.id ? null : staff)}
                  className={cn(
                    "w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left",
                    selectedStaff?.id === staff.id
                      ? "bg-primary/10 border border-primary/30"
                      : "hover:bg-muted/50"
                  )}
                >
                  <div className="relative">
                    <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center text-sm font-medium text-foreground">
                      {staff.avatar}
                    </div>
                    <span
                      className={cn(
                        "absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-background",
                        staff.status === 'online' && "bg-green-500",
                        staff.status === 'away' && "bg-amber-500",
                        staff.status === 'offline' && "bg-muted-foreground"
                      )}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{staff.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{staff.role}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Messages Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Compose Message */}
            <div className="glass-card neo-shadow rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <h3 className="font-medium text-foreground">
                  {selectedStaff ? `Private message to ${selectedStaff.name}` : 'Broadcast to all staff'}
                </h3>
                {selectedStaff && (
                  <button
                    onClick={() => setSelectedStaff(null)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    (clear)
                  </button>
                )}
              </div>
              <div className="flex gap-3">
                <div className="flex-1 space-y-2">
                  <Input
                    placeholder={selectedStaff ? `Subject (to ${selectedStaff.name})` : 'Subject (announcement)'}
                    value={newSubject}
                    onChange={(e) => setNewSubject(e.target.value)}
                    className="bg-muted/50 border-border/50"
                  />
                  <Textarea
                    placeholder={selectedStaff ? `Message ${selectedStaff.name}...` : "Message all staff..."}
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    className="bg-muted/50 border-border/50 resize-none"
                    rows={2}
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!newSubject.trim() || !newMessage.trim() || sendPrivateMutation.isPending || sendPublicMutation.isPending}
                  className="gradient-primary shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Pinned Messages */}
            {pinnedMessages.length > 0 && (
              <div className="glass-card neo-shadow rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Pin className="h-4 w-4 text-primary" />
                  <h3 className="font-medium text-foreground">Pinned Announcements</h3>
                </div>
                <div className="space-y-3">
                  {pinnedMessages.map((message) => (
                    <div
                      key={message.id}
                      className="p-4 rounded-xl bg-primary/5 border border-primary/20"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-foreground">{message.senderName}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(message.timestamp)} at {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-foreground">{message.subject}</p>
                          <p className="text-sm text-foreground/80">{message.content}</p>
                        </div>
                        <button
                          onClick={() => togglePin(message.id)}
                          className="p-1.5 rounded-lg hover:bg-background/50 text-primary"
                        >
                          <PinOff className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Message Tabs & List */}
            <div className="glass-card neo-shadow rounded-2xl p-5">
              <div className="flex items-center gap-4 mb-4 border-b border-border/50 pb-3">
                <button
                  onClick={() => setActiveTab('all')}
                  className={cn(
                    "text-sm font-medium pb-2 border-b-2 transition-colors",
                    activeTab === 'all'
                      ? "text-primary border-primary"
                      : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  All Staff Messages
                </button>
                <button
                  onClick={() => setActiveTab('private')}
                  className={cn(
                    "text-sm font-medium pb-2 border-b-2 transition-colors",
                    activeTab === 'private'
                      ? "text-primary border-primary"
                      : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  Private Messages
                </button>
              </div>

              <div className="space-y-3">
                {regularMessages.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    {activeTab === 'private' ? 'No private messages yet' : 'No public messages yet'}
                  </p>
                ) : (
                  regularMessages.map((message) => (
                    <div
                      key={message.id}
                      className="p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-foreground">{message.senderName}</span>
                            {message.isPrivate && (
                              <span
                                className={cn(
                                  "text-xs px-2 py-0.5 rounded-full",
                                  message.senderId === currentDoctorId
                                    ? "bg-primary/10 text-primary"
                                    : "bg-emerald-500/10 text-emerald-600"
                                )}
                              >
                                {getPrivateDirectionLabel(message)}
                              </span>
                            )}
                            {!message.isPrivate && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-foreground">
                                Public
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {formatDate(message.timestamp)} at {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-foreground">{message.subject}</p>
                          <p className="text-sm text-foreground/80">{message.content}</p>
                        </div>
                        {!message.isPrivate && (
                          <button
                            onClick={() => togglePin(message.id)}
                            className="p-1.5 rounded-lg hover:bg-background/50 text-muted-foreground hover:text-primary"
                          >
                            <Pin className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
