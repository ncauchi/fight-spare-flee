import { type Message } from "./Game";
import { ListGroup, Form, Stack, Button } from "react-bootstrap";
import { useSocketEmit } from "./SocketContext";
import { useState, useRef, useEffect } from "react";
import { usePlayerName } from "./NameContext";

interface Props {
  messages: Message[];
  gameName: string;
  gameOwner: string;
}

function ChatWindow({ gameName, gameOwner, messages }: Props) {
  const emit = useSocketEmit();
  const [message, setMessage] = useState("");
  const playerName = usePlayerName();
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleSendChat = () => {
    if (message) {
      emit("CHAT", playerName, message);
      setMessage("");
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  return (
    <Stack className="my-auto lobby-chat">
      <ListGroup className="overflow-y-auto overflow-x-hidden m-2">
        {messages.map((message, index) => (
          <ListGroup.Item key={index}>
            {message.player == "SERVER123" ? gameName : message.player}
            {message.player == "SERVER123" && <span style={{ color: "#D2691E" }}>{"(Server)"}</span>}
            {message.player == gameOwner && <span style={{ color: "blue" }}>{"(Owner)"}</span>}: {message.text}
          </ListGroup.Item>
        ))}
        <div ref={chatEndRef} />
      </ListGroup>
      <Stack direction="horizontal" gap={2} className="m-2 mt-auto">
        <Form.Control
          type="text"
          placeholder="Send Message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSendChat();
            }
          }}
        />
        <Button variant="primary" onClick={handleSendChat}>
          Send
        </Button>
      </Stack>
    </Stack>
  );
}

export default ChatWindow;
