import uuid

class TrackType:
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    IMAGE = "image"
    LOGO = "logo"
    COVER = "cover"
    BROLL = "broll"

class Clip:
    def __init__(self, name: str, source_path: str, start_time: int, duration: int, clip_type: str = TrackType.VIDEO, **kwargs):
        """
        :param name: 显示名称
        :param source_path: 源文件路径 (或者字幕文本)
        :param start_time: 片段在时间轴上的起始时间 (毫秒)
        :param duration: 片段的持续时长 (毫秒)
        :param clip_type: 轨道类型
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.source_path = source_path
        self.start_time = max(0, start_time)
        self.duration = max(0, duration)
        self.clip_type = clip_type
        
        # 扩展属性 (如图片坐标、字幕内容等)
        self.meta = kwargs

    @property
    def end_time(self) -> int:
        return self.start_time + self.duration
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "source_path": self.source_path,
            "start_time": self.start_time,
            "duration": self.duration,
            "clip_type": self.clip_type,
            "meta": self.meta
        }
        
    @classmethod
    def from_dict(cls, data):
        clip = cls(
            name=data.get("name", ""),
            source_path=data.get("source_path", ""),
            start_time=data.get("start_time", 0),
            duration=data.get("duration", 0),
            clip_type=data.get("clip_type", TrackType.VIDEO),
            **data.get("meta", {})
        )
        if "id" in data:
            clip.id = data["id"]
        return clip

class Track:
    def __init__(self, name: str, track_type: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.track_type = track_type
        self.clips = [] # List of Clip
        
    def add_clip(self, clip: Clip):
        self.clips.append(clip)
        self.sort_clips()
        
    def remove_clip(self, clip_id: str):
        self.clips = [c for c in self.clips if c.id != clip_id]
        
    def sort_clips(self):
        self.clips.sort(key=lambda c: c.start_time)
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "track_type": self.track_type,
            "clips": [c.to_dict() for c in self.clips]
        }
        
    @classmethod
    def from_dict(cls, data):
        track = cls(name=data.get("name", ""), track_type=data.get("track_type", TrackType.VIDEO))
        if "id" in data:
            track.id = data["id"]
        for c_data in data.get("clips", []):
            track.add_clip(Clip.from_dict(c_data))
        return track

class Timeline:
    def __init__(self):
        self.tracks = []
        
    def add_track(self, track: Track):
        self.tracks.append(track)
        
    def remove_track(self, track_id: str):
        self.tracks = [t for t in self.tracks if t.id != track_id]
        
    def get_tracks_by_type(self, track_type: str) -> list:
        return [t for t in self.tracks if t.track_type == track_type]

    def get_duration(self) -> int:
        max_duration = 0
        for track in self.tracks:
            for clip in track.clips:
                if clip.end_time > max_duration:
                    max_duration = clip.end_time
        return max_duration
        
    def clear(self):
        self.tracks = []
        
    def to_dict(self):
        return {
            "tracks": [t.to_dict() for t in self.tracks]
        }
        
    @classmethod
    def from_dict(cls, data):
        timeline = cls()
        for t_data in data.get("tracks", []):
            timeline.add_track(Track.from_dict(t_data))
        return timeline
