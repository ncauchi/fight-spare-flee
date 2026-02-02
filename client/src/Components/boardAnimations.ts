import { replace } from "react-router-dom";
import {
  type Animation,
  type ItemAnimContent,
  type ItemInfo,
  type Location,
  type MonsterInfo,
  type SimpleLocation,
} from "../api_wrapper";
import React, { useState, useCallback, useRef } from "react";
import { type TargetAndTransition, type Transition, type VariantLabels } from "motion";
import { tr } from "motion/react-m";

export function useBoardAnimations() {
  const [animations, setAnimations] = useState<AnimationInfo[]>([]);
  const refRegistry = useRef(new Map<string, HTMLDivElement>());
  const pendingAnimations = useRef<Animation[]>([]);
  const animId = useRef(0);

  const tryProcessPending = useCallback(() => {
    const stillPending: Animation[] = [];
    for (const event of pendingAnimations.current) {
      const result = processAnimationEvent(event, animId, refRegistry.current);
      if (result) {
        setAnimations((prev) => [...prev, result]);
      } else {
        stillPending.push(event);
      }
    }
    pendingAnimations.current = stillPending;
  }, []);

  const onAnimationEvent = useCallback((event: Animation) => {
    const result = processAnimationEvent(event, animId, refRegistry.current);
    if (result) {
      setAnimations((prev) => [...prev, result]);
    } else {
      // Refs not ready yet, queue for later
      pendingAnimations.current.push(event);
    }
  }, []);

  const removeAnimation = useCallback((id: number) => {
    setAnimations((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const registerRef = useCallback(
    (id: string, el: HTMLDivElement | null, type: "item" | "monster" | null = null) => {
      if (type == "item") {
        id = "item" + id;
      } else if (type == "monster") {
        id = "monster" + id;
      }
      if (el) {
        // Only process pending if this is a new ref or the element changed
        const existingEl = refRegistry.current.get(id);
        if (existingEl !== el) {
          refRegistry.current.set(id, el);
          // New ref registered, try to process any pending animations
          if (pendingAnimations.current.length > 0) {
            tryProcessPending();
          }
        }
      } else {
        refRegistry.current.delete(id);
      }
    },
    [tryProcessPending],
  );

  return { animations, onAnimationEvent, removeAnimation, registerRef };
}

interface BaseAnimationInfo {
  transition: Transition<any>;
  initial: boolean | TargetAndTransition | VariantLabels | undefined;
  animate: boolean | TargetAndTransition | VariantLabels | undefined;
  id: number;
}

export interface ItemAnimationInfo extends BaseAnimationInfo {
  object: "item";
  itemInfo: ItemInfo;
  replaceId: number | null;
}

export interface MonsterAnimationInfo extends BaseAnimationInfo {
  object: "monster";
  monsterInfo: MonsterInfo;
  replaceId: number | null;
}

export interface CoinsAnimationInfo extends BaseAnimationInfo {
  object: "coins";
}

export interface StarsAnimationInfo extends BaseAnimationInfo {
  object: "stars";
}

export type AnimationInfo = ItemAnimationInfo | MonsterAnimationInfo | CoinsAnimationInfo | StarsAnimationInfo;

const processAnimationEvent = (
  event: Animation,
  id: React.RefObject<number>,
  refs: Map<string, HTMLDivElement>,
): AnimationInfo | null => {
  console.log("processing animation");
  const start = processLocation(event.source, refs);
  if (!start) return null;

  const end = event.destination ? processLocation(event.destination, refs) : start;
  const uid = id.current;
  id.current = uid + 1;
  if (!end) return null;
  const animInfo: BaseAnimationInfo = {
    id: uid,
    transition: { type: "spring", duration: 0.4, bounce: 0.25 },
    initial: {
      x: start.x,
      y: start.y,
    },
    animate: {
      x: end.x,
      y: end.y,
    },
  };
  let style: Transition = { type: "spring", duration: 0.4, bounce: 0.25 };
  switch (event.content.type) {
    case "item":
      if (event.content.style == "attack") {
        style = { type: "spring", duration: 0.7, bounce: 0.25 };
      }
      return { ...animInfo, object: "item", transition: style, itemInfo: event.content.item, replaceId: end.replaceId };
    case "monster":
      if (event.content.style == "appear") {
        const transition: Transition = {
          type: "keyframes",
          bounce: 1,
          duration: 0.7,
          times: [0, 0.3, 1],
        };
        const animate = {
          scale: [1, 1.3, 1],
          x: [start.x, lerp(start.x, end.x, 0.3), end.x],
          y: [start.y, lerp(start.y, end.y, 0.8) - 50, end.y],
        };
        return {
          ...animInfo,
          object: "monster",
          transition: transition,
          animate: animate,
          initial: { x: start.x, y: start.y, scale: 1 },
          monsterInfo: event.content.monster,
          replaceId: end.replaceId,
        };
      }
      return {
        ...animInfo,
        object: "monster",
        transition: style,
        monsterInfo: event.content.monster,
        replaceId: end.replaceId,
      };
    case "coin":
      return { ...animInfo, object: "coins" };
    case "star":
      return { ...animInfo, object: "stars" };
  }
};

const processLocation = (
  location: Location,
  refs: Map<string, HTMLDivElement>,
): { replaceId: number | null; x: number; y: number } | null => {
  let el: HTMLDivElement | null = null;
  let replace: number | null = null;
  if (typeof location === "string") {
    el = refs.get(location) ?? null;
  } else {
    switch (location.object) {
      case "hand":
        el = refs.get(`item${location.id}`) ?? null;
        replace = location.id;
        break;
      case "monster":
        el = refs.get(`monster${location.id}`) ?? null;
        replace = location.id;
        break;
    }
  }
  const board = refs.get("board");
  if (el == null || board == undefined) {
    // Refs not ready yet
    return null;
  }

  const boardRect = board.getBoundingClientRect();
  const elRect = el.getBoundingClientRect();
  return { replaceId: replace, x: elRect.left - boardRect.left, y: elRect.top - boardRect.top };
};

const lerp = (start: number, end: number, time: number): number => {
  const res = start + time * (end - start);
  return res;
};
