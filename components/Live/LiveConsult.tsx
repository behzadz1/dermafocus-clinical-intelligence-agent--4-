import React, { useEffect, useRef, useState } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from "@google/genai";
import { SYSTEM_INSTRUCTION } from '../../constants';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Activity, Loader2, Camera, BrainCircuit } from 'lucide-react';

const LiveConsult: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const pipVideoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoIntervalRef = useRef<number | null>(null);
  const sessionRef = useRef<any>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  // --- AUDIO UTILS ---
  const encodeAudio = (bytes: Uint8Array) => {
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const decodeAudio = (base64: string) => {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  };

  const createBlob = (data: Float32Array) => {
    const l = data.length;
    const int16 = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      int16[i] = data[i] * 32768;
    }
    return {
      data: encodeAudio(new Uint8Array(int16.buffer)),
      mimeType: 'audio/pcm;rate=16000',
    };
  };

  const decodeAudioData = async (
    data: Uint8Array,
    ctx: AudioContext,
    sampleRate: number = 24000,
    numChannels: number = 1,
  ): Promise<AudioBuffer> => {
    const dataInt16 = new Int16Array(data.buffer);
    const frameCount = dataInt16.length / numChannels;
    const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

    for (let channel = 0; channel < numChannels; channel++) {
      const channelData = buffer.getChannelData(channel);
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
      }
    }
    return buffer;
  };

  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () => {
         const result = reader.result as string;
         resolve(result.split(',')[1]);
      };
      reader.readAsDataURL(blob);
    });
  };

  // --- MAIN LOGIC ---

  const stopConnection = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoIntervalRef.current) {
      clearInterval(videoIntervalRef.current);
      videoIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    sourcesRef.current.forEach(source => source.stop());
    sourcesRef.current.clear();
    
    setIsConnected(false);
    setIsConnecting(false);
    setIsAiProcessing(false);
  };

  useEffect(() => {
    return () => stopConnection();
  }, []);

  const startConsultation = async () => {
    setError(null);
    setIsConnecting(true);

    try {
      if (!process.env.API_KEY) throw new Error("API Key missing");
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
            sampleRate: 16000,
            channelCount: 1,
        }, 
        video: {
            width: 1280,
            height: 720
        } 
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      if (pipVideoRef.current) pipVideoRef.current.srcObject = stream;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioContextClass({ sampleRate: 24000 });
      audioContextRef.current = audioCtx;
      
      const inputCtx = new AudioContextClass({ sampleRate: 16000 });
      const inputSource = inputCtx.createMediaStreamSource(stream);
      const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
      
      inputSource.connect(scriptProcessor);
      scriptProcessor.connect(inputCtx.destination);

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-09-2025',
        config: {
            systemInstruction: SYSTEM_INSTRUCTION + "\n\nIMPORTANT: You are now in a LIVE VIDEO CONSULTATION with a clinician. Be concise, professional, and guide them through visual assessments if they show you anatomy. You are the second set of eyes for the clinician.",
            responseModalities: [Modality.AUDIO],
            speechConfig: {
                voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } }
            }
        },
        callbacks: {
            onopen: () => {
                setIsConnected(true);
                setIsConnecting(false);

                scriptProcessor.onaudioprocess = (e) => {
                    if (isMuted) return;
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcmBlob = createBlob(inputData);
                    sessionPromise.then((session) => {
                        session.sendRealtimeInput({ media: pcmBlob });
                    });
                };

                videoIntervalRef.current = window.setInterval(() => {
                    if (!canvasRef.current || !videoRef.current || !isVideoEnabled) return;
                    
                    const ctx = canvasRef.current.getContext('2d');
                    if (!ctx) return;

                    canvasRef.current.width = videoRef.current.videoWidth;
                    canvasRef.current.height = videoRef.current.videoHeight;
                    ctx.drawImage(videoRef.current, 0, 0);

                    canvasRef.current.toBlob(async (blob) => {
                        if (blob) {
                            const base64Data = await blobToBase64(blob);
                            sessionPromise.then((session) => {
                                session.sendRealtimeInput({
                                    media: { data: base64Data, mimeType: 'image/jpeg' }
                                });
                            });
                        }
                    }, 'image/jpeg', 0.6);
                }, 1000); 
            },
            onmessage: async (msg: LiveServerMessage) => {
                if (msg.serverContent?.modelTurn) {
                  setIsAiProcessing(true);
                }
                
                const base64Audio = msg.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data;
                if (base64Audio && audioContextRef.current) {
                    const ctx = audioContextRef.current;
                    nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
                    
                    try {
                        const audioBuffer = await decodeAudioData(
                            decodeAudio(base64Audio),
                            ctx
                        );
                        
                        const source = ctx.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(ctx.destination);
                        
                        source.addEventListener('ended', () => {
                            sourcesRef.current.delete(source);
                            if (sourcesRef.current.size === 0) setIsAiProcessing(false);
                        });
                        
                        source.start(nextStartTimeRef.current);
                        nextStartTimeRef.current += audioBuffer.duration;
                        sourcesRef.current.add(source);
                    } catch (e) {
                        console.error("Audio Decode Error", e);
                        setIsAiProcessing(false);
                    }
                }
            },
            onclose: () => {
                stopConnection();
            },
            onerror: (err) => {
                console.error("Gemini Live Error", err);
                setError("Connection error. Please try again.");
                stopConnection();
            }
        }
      });
      
      sessionRef.current = sessionPromise;

    } catch (err) {
        console.error("Setup Error", err);
        setError("Failed to access camera/microphone or connect to AI.");
        setIsConnecting(false);
    }
  };

  const toggleMute = () => setIsMuted(!isMuted);
  const toggleVideo = () => setIsVideoEnabled(!isVideoEnabled);

  return (
    <div className="flex flex-col h-full bg-slate-950 relative overflow-hidden">
      <canvas ref={canvasRef} className="hidden" />

      {/* Main Video/Visualization Area */}
      <div className="flex-1 relative flex items-center justify-center bg-black">
        {isConnected ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-12">
            <div className="relative w-64 h-64 md:w-80 md:h-80 flex items-center justify-center">
               <div className={`absolute inset-0 bg-teal-500/10 rounded-full blur-3xl transition-opacity duration-1000 ${isAiProcessing ? 'opacity-100' : 'opacity-30'}`} />
               <div className={`relative w-48 h-48 md:w-64 md:h-64 rounded-full border-2 border-teal-500/20 flex items-center justify-center transition-transform duration-500 ${isAiProcessing ? 'scale-110 border-teal-500/40' : 'scale-100'}`}>
                  <BrainCircuit size={80} className={`text-teal-400 transition-all duration-300 ${isAiProcessing ? 'animate-pulse' : 'opacity-60'}`} />
                  
                  {/* Orbiting particles or rings for visual flair */}
                  <div className={`absolute inset-0 border border-teal-500/10 rounded-full animate-[spin_10s_linear_infinite]`} />
                  <div className={`absolute -inset-4 border border-dashed border-teal-500/5 rounded-full animate-[spin_20s_linear_infinite_reverse]`} />
               </div>
            </div>
            <div className="mt-12 text-center">
               <p className="text-teal-500 font-bold tracking-[0.3em] uppercase text-sm mb-2">Secure Link Established</p>
               <h3 className="text-white text-2xl font-light">Expert Intelligence Monitoring</h3>
               <div className="flex justify-center gap-1 mt-6 h-4 items-end">
                  {[...Array(8)].map((_, i) => (
                    <div 
                      key={i} 
                      className={`w-1 bg-teal-500/40 rounded-full transition-all duration-150 ${isAiProcessing ? 'animate-bounce' : 'h-1'}`}
                      style={{ animationDelay: `${i * 0.1}s`, height: isAiProcessing ? '100%' : '10%' }}
                    />
                  ))}
               </div>
            </div>
          </div>
        ) : (
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted 
            className={`w-full h-full object-cover transition-opacity duration-700 ${!isConnected && !isConnecting ? 'opacity-40 grayscale' : 'opacity-0'}`} 
          />
        )}
        
        {(!isConnected && !isConnecting) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-6 text-center z-10">
                <div className="w-24 h-24 bg-teal-600 rounded-3xl flex items-center justify-center mb-8 shadow-[0_0_50px_rgba(20,184,166,0.4)] rotate-3 hover:rotate-0 transition-transform cursor-pointer" onClick={startConsultation}>
                    <Camera size={44} />
                </div>
                <h2 className="text-3xl font-bold mb-3 tracking-tight">Live Clinical Consult</h2>
                <p className="text-slate-400 max-w-md mb-10 text-lg leading-relaxed">
                    Initiate a multimodal session with the CKPA expert. <br/>
                    AI-powered visual analysis and voice guidance.
                </p>
                <button 
                    onClick={startConsultation}
                    className="bg-white text-slate-900 px-10 py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:scale-105 transition-all flex items-center gap-4 shadow-2xl hover:bg-teal-50"
                >
                    <Activity size={20} className="text-teal-600 animate-pulse" />
                    Open Secure Uplink
                </button>
                <div className="mt-8 flex items-center gap-2 px-4 py-2 bg-slate-900/50 backdrop-blur-md rounded-full border border-slate-800">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Systems Ready</span>
                </div>
            </div>
        )}

        {isConnecting && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-white bg-slate-950/90 z-20">
                <Loader2 size={56} className="animate-spin text-teal-500 mb-6" />
                <p className="text-xl font-bold tracking-widest uppercase text-teal-500/80 animate-pulse">Syncing Protocols...</p>
                <p className="text-slate-500 mt-2 text-sm font-medium">Verifying medical credentials & IFU database</p>
            </div>
        )}

        {/* AI EXPERT LABEL & STATUS INDICATOR */}
        {isConnected && (
            <div className="absolute top-8 right-8 z-30">
              <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-4 shadow-2xl min-w-[200px]">
                  <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2.5">
                          <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_10px_rgba(20,184,166,0.5)] ${isAiProcessing ? 'bg-teal-400 animate-ping' : 'bg-teal-500'}`} />
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-black text-slate-200 uppercase tracking-wider">DermaAI Expert</span>
                            {isAiProcessing && <Loader2 size={12} className="animate-spin text-teal-400" />}
                          </div>
                      </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                       <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Voice Analysis</span>
                       <span className="text-[10px] font-bold text-teal-500/80">Active</span>
                    </div>
                    <div className="flex items-center justify-between">
                       <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Vision Stream</span>
                       <span className={`text-[10px] font-bold transition-colors ${isVideoEnabled ? 'text-teal-500/80' : 'text-red-500/80'}`}>
                         {isVideoEnabled ? '1080p' : 'Paused'}
                       </span>
                    </div>
                    <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                       <div className={`h-full bg-teal-500 transition-all duration-300 ${isAiProcessing ? 'w-full opacity-100' : 'w-1/3 opacity-30'}`} />
                    </div>
                  </div>
              </div>
            </div>
        )}

        {/* REFINED PIP LOCAL PREVIEW (Bottom Right Corner) */}
        {isConnected && (
          <div className="absolute bottom-24 right-6 z-30 group animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className={`relative w-40 md:w-56 aspect-[3/4] bg-slate-900 rounded-3xl border-2 overflow-hidden shadow-2xl transition-all duration-500 ${isVideoEnabled ? 'border-teal-500/40' : 'border-red-500/20 grayscale opacity-50'}`}>
                <video 
                    ref={pipVideoRef} 
                    autoPlay 
                    playsInline 
                    muted 
                    className="w-full h-full object-cover" 
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none" />
                <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 bg-black/40 backdrop-blur-md rounded-lg border border-white/10">
                   <div className={`w-1.5 h-1.5 rounded-full ${isVideoEnabled ? 'bg-red-500 animate-pulse' : 'bg-slate-500'}`} />
                   <span className="text-[9px] font-black text-white uppercase tracking-widest">Clinician</span>
                </div>
                {!isVideoEnabled && (
                  <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm">
                    <VideoOff size={24} className="text-slate-400" />
                  </div>
                )}
            </div>
          </div>
        )}
        
        {error && (
            <div className="absolute top-8 left-8 right-8 bg-red-600 text-white p-5 rounded-2xl shadow-2xl flex items-center gap-4 z-40 animate-in fade-in slide-in-from-top-4">
                <div className="bg-red-500 p-2 rounded-lg">
                  <Activity size={24} />
                </div>
                <div>
                   <p className="font-bold">System Exception</p>
                   <p className="text-sm opacity-90">{error}</p>
                </div>
                <button onClick={() => setError(null)} className="ml-auto bg-white/10 hover:bg-white/20 px-4 py-2 rounded-xl text-sm font-bold transition-colors">Dismiss</button>
            </div>
        )}
      </div>

      {/* Modern Floating Controls Bar */}
      {isConnected && (
          <div className="absolute bottom-8 left-0 right-0 flex items-center justify-center z-40 pointer-events-none">
            <div className="bg-slate-900/90 backdrop-blur-2xl border border-slate-700/50 p-4 rounded-[2.5rem] flex items-center gap-6 shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto">
              <button 
                  onClick={toggleMute}
                  className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isMuted ? 'bg-red-500/20 text-red-500' : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'}`}
                  title={isMuted ? "Unmute Mic" : "Mute Mic"}
              >
                  {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
              </button>
              
              <button 
                  onClick={stopConnection}
                  className="bg-red-600 hover:bg-red-700 text-white w-20 h-20 rounded-[2rem] shadow-xl shadow-red-900/20 hover:scale-105 active:scale-95 transition-all flex items-center justify-center group"
                  title="Disconnect"
              >
                  <PhoneOff size={32} className="group-hover:rotate-12 transition-transform" />
              </button>

              <button 
                  onClick={toggleVideo}
                  className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${!isVideoEnabled ? 'bg-red-500/20 text-red-500' : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'}`}
                  title={isVideoEnabled ? "Pause Vision" : "Resume Vision"}
              >
                  {!isVideoEnabled ? <VideoOff size={24} /> : <Video size={24} />}
              </button>
            </div>
          </div>
      )}
    </div>
  );
};

export default LiveConsult;