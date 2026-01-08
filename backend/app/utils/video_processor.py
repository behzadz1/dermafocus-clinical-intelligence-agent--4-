"""
Video Processing for RAG
Extracts audio and transcribes using OpenAI Whisper
"""

import os
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Video processing (optional dependencies)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: Whisper not installed. Video transcription disabled.")
    print("To enable: pip install openai-whisper")

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: MoviePy not installed. Video processing disabled.")
    print("To enable: pip install moviepy")

from .chunking import TextChunker


class VideoProcessor:
    """
    Process video files for RAG ingestion
    - Extract audio
    - Transcribe with Whisper
    - Create timestamped chunks
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            chunk_size: Target size for text chunks
            chunk_overlap: Overlap between chunks
        """
        self.whisper_model_name = whisper_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        
        # Load Whisper model (lazy loading)
        self._whisper_model = None
    
    @property
    def whisper_model(self):
        """Lazy load Whisper model"""
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not installed")
        
        if self._whisper_model is None:
            print(f"Loading Whisper model: {self.whisper_model_name}")
            self._whisper_model = whisper.load_model(self.whisper_model_name)
        
        return self._whisper_model
    
    def process_video(
        self,
        video_path: str,
        doc_id: str = None,
        doc_type: str = "video"
    ) -> Dict[str, Any]:
        """
        Process a video file completely
        
        Args:
            video_path: Path to video file
            doc_id: Unique document identifier
            doc_type: Type of document
            
        Returns:
            Dictionary with processed video data:
            {
                "doc_id": str,
                "doc_type": str,
                "metadata": dict,
                "transcript": str,
                "segments": list,
                "chunks": list
            }
        """
        if not WHISPER_AVAILABLE or not MOVIEPY_AVAILABLE:
            raise RuntimeError("Video processing dependencies not installed")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = Path(video_path).stem
        
        print(f"Processing video: {video_path}")
        
        # Extract metadata
        metadata = self._extract_video_metadata(video_path)
        metadata["doc_id"] = doc_id
        metadata["doc_type"] = doc_type
        metadata["source_file"] = os.path.basename(video_path)
        metadata["processed_at"] = datetime.utcnow().isoformat()
        
        # Extract audio to temporary file
        audio_path = self._extract_audio(video_path)
        
        try:
            # Transcribe audio
            transcript_data = self._transcribe_audio(audio_path)
            
            # Create chunks from transcript
            chunks = self._create_chunks_from_transcript(
                transcript_data,
                metadata
            )
            
            # Combine all segments into full transcript
            full_transcript = " ".join(
                seg["text"] for seg in transcript_data["segments"]
            )
            
            return {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "metadata": metadata,
                "transcript": full_transcript,
                "segments": transcript_data["segments"],
                "chunks": chunks,
                "stats": {
                    "duration_seconds": metadata.get("duration", 0),
                    "num_segments": len(transcript_data["segments"]),
                    "num_chunks": len(chunks),
                    "total_chars": len(full_transcript)
                }
            }
        
        finally:
            # Clean up temporary audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    def _extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract metadata from video file
        
        Args:
            video_path: Path to video
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        try:
            clip = VideoFileClip(video_path)
            metadata["duration"] = clip.duration  # seconds
            metadata["fps"] = clip.fps
            metadata["size"] = clip.size  # (width, height)
            metadata["width"] = clip.w
            metadata["height"] = clip.h
            clip.close()
        except Exception as e:
            print(f"Warning: Could not extract video metadata: {e}")
        
        return metadata
    
    def _extract_audio(self, video_path: str) -> str:
        """
        Extract audio from video to temporary WAV file
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to temporary audio file
        """
        print("Extracting audio from video...")
        
        # Create temporary file
        temp_audio = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )
        audio_path = temp_audio.name
        temp_audio.close()
        
        try:
            # Extract audio using moviepy
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(
                audio_path,
                verbose=False,
                logger=None
            )
            clip.close()
            
            print(f"Audio extracted to: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"Error extracting audio: {e}")
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise
    
    def _transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcript and segments
        """
        print("Transcribing audio with Whisper...")
        
        try:
            result = self.whisper_model.transcribe(
                audio_path,
                verbose=False
            )
            
            print(f"Transcription complete. Language: {result.get('language', 'unknown')}")
            
            return {
                "text": result["text"],
                "segments": result["segments"],
                "language": result.get("language", "unknown")
            }
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            raise
    
    def _create_chunks_from_transcript(
        self,
        transcript_data: Dict[str, Any],
        base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from transcribed segments
        
        Args:
            transcript_data: Transcript with segments
            base_metadata: Base metadata
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Group segments into chunks by time
        current_chunk_text = []
        current_chunk_start = None
        current_chunk_end = None
        current_length = 0
        
        for segment in transcript_data["segments"]:
            text = segment["text"].strip()
            start_time = segment["start"]
            end_time = segment["end"]
            
            if current_chunk_start is None:
                current_chunk_start = start_time
            
            current_chunk_text.append(text)
            current_chunk_end = end_time
            current_length += len(text)
            
            # Create chunk if we've reached target size
            if current_length >= self.chunk_size:
                chunk_text = " ".join(current_chunk_text)
                
                chunks.append({
                    "text": chunk_text,
                    "chunk_id": f"{base_metadata['doc_id']}_chunk{len(chunks)}",
                    "metadata": {
                        **base_metadata,
                        "chunk_index": len(chunks),
                        "start_time": current_chunk_start,
                        "end_time": current_chunk_end,
                        "timestamp": self._format_timestamp(current_chunk_start)
                    }
                })
                
                # Reset for next chunk (with overlap)
                overlap_text = chunk_text[-self.chunk_overlap:]
                current_chunk_text = [overlap_text]
                current_length = len(overlap_text)
                current_chunk_start = start_time
        
        # Add final chunk
        if current_chunk_text:
            chunk_text = " ".join(current_chunk_text)
            chunks.append({
                "text": chunk_text,
                "chunk_id": f"{base_metadata['doc_id']}_chunk{len(chunks)}",
                "metadata": {
                    **base_metadata,
                    "chunk_index": len(chunks),
                    "start_time": current_chunk_start,
                    "end_time": current_chunk_end,
                    "timestamp": self._format_timestamp(current_chunk_start)
                }
            })
        
        return chunks
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds as MM:SS timestamp
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def extract_keyframes(
        self,
        video_path: str,
        num_frames: int = 10
    ) -> List[str]:
        """
        Extract keyframes from video (for future image analysis)
        
        Args:
            video_path: Path to video
            num_frames: Number of frames to extract
            
        Returns:
            List of paths to extracted frame images
        """
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError("MoviePy not installed")
        
        print(f"Extracting {num_frames} keyframes...")
        
        frame_paths = []
        
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            interval = duration / (num_frames + 1)
            
            for i in range(1, num_frames + 1):
                timestamp = i * interval
                frame = clip.get_frame(timestamp)
                
                # Save frame
                frame_path = tempfile.NamedTemporaryFile(
                    suffix=f"_frame{i}.jpg",
                    delete=False
                )
                
                # Convert to PIL Image and save
                from PIL import Image
                img = Image.fromarray(frame)
                img.save(frame_path.name)
                frame_paths.append(frame_path.name)
            
            clip.close()
            
        except Exception as e:
            print(f"Error extracting keyframes: {e}")
            # Clean up any created files
            for path in frame_paths:
                if os.path.exists(path):
                    os.remove(path)
            raise
        
        return frame_paths


def is_video_processing_available() -> bool:
    """Check if video processing dependencies are available"""
    return WHISPER_AVAILABLE and MOVIEPY_AVAILABLE


def get_missing_dependencies() -> List[str]:
    """Get list of missing dependencies for video processing"""
    missing = []
    if not WHISPER_AVAILABLE:
        missing.append("openai-whisper")
    if not MOVIEPY_AVAILABLE:
        missing.append("moviepy")
    return missing
