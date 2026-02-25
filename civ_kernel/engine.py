from __future__ import annotations
import heapq
import pickle
from pathlib import Path
from tqdm import tqdm
from .models import Event, World
from . import config


class EventEngine:
    def __init__(self, world: World) -> None:
        self.world = world
        self._handlers: dict[str, callable] = {}

    def register(self, event_type: str, handler: callable) -> None:
        self._handlers[event_type] = handler

    def schedule(self, event: Event) -> None:
        heapq.heappush(self.world.event_queue, event)

    def run(self) -> None:
        w = self.world
        checkpoint_dir = Path('checkpoints')
        checkpoint_dir.mkdir(exist_ok=True)

        # 进度条：基于虚拟时间
        with tqdm(total=config.MAX_VIRTUAL_TIME, desc="模拟进度", unit="时间单位") as pbar:
            last_clock = 0.0
            next_checkpoint = config.CHECKPOINT_INTERVAL

            while w.event_queue and w.clock < config.MAX_VIRTUAL_TIME:
                event = heapq.heappop(w.event_queue)
                w.clock = event.trigger_time
                w.event_count += 1

                # 更新进度条
                delta = w.clock - last_clock
                pbar.update(delta)
                last_clock = w.clock

                self.dispatch(event)

                if w.event_count % config.METRICS_INTERVAL == 0:
                    self._record_metrics()

                # Checkpoint 保存
                if w.clock >= next_checkpoint:
                    self._save_checkpoint(checkpoint_dir, int(next_checkpoint))
                    next_checkpoint += config.CHECKPOINT_INTERVAL

    def dispatch(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler:
            handler(self.world, event)

    def _record_metrics(self) -> None:
        from .metrics import snapshot
        self.world.metrics_log.append(snapshot(self.world))

    def _save_checkpoint(self, checkpoint_dir: Path, step: int) -> None:
        """保存 checkpoint 到文件（精简版）"""
        # 1. 清理 exchange_history（只保留最近10条，metrics只用这些）
        for agent in self.world.agents.values():
            if len(agent.exchange_history) > 10:
                agent.exchange_history = agent.exchange_history[-10:]

        # 2. 暂存并清空 metrics_log（checkpoint不需要，最终输出时重新计算）
        metrics_backup = self.world.metrics_log
        self.world.metrics_log = []

        # 3. 计算当前快照（用于变动率分析）
        from .metrics import snapshot
        current_snapshot = snapshot(self.world)

        # 4. 保存
        checkpoint_path = checkpoint_dir / f'checkpoint_{step}.pkl'
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(self.world, f)

        # 5. 恢复 metrics_log
        self.world.metrics_log = metrics_backup

        # 6. 计算变动率（与上一个checkpoint比较）
        if hasattr(self, '_last_checkpoint_snapshot'):
            last = self._last_checkpoint_snapshot
            gini_change = abs(current_snapshot['gini'] - last['gini'])
            org_change = abs(current_snapshot['n_orgs'] - last['n_orgs'])
            wealth_change = abs(current_snapshot['avg_wealth'] - last['avg_wealth']) / max(last['avg_wealth'], 0.01)

            file_size = checkpoint_path.stat().st_size / 1024
            tqdm.write(f"✓ Checkpoint {step}: {file_size:.1f}KB | "
                      f"ΔGini={gini_change:.4f} ΔOrgs={org_change} ΔWealth={wealth_change:.2%}")
        else:
            file_size = checkpoint_path.stat().st_size / 1024
            tqdm.write(f"✓ Checkpoint {step}: {file_size:.1f}KB (首个checkpoint)")

        self._last_checkpoint_snapshot = current_snapshot
