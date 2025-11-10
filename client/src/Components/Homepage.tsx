import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "react-bootstrap/Button";
import Alert from "react-bootstrap/Alert";
import Form from "react-bootstrap/Form";
import { useSetPlayerName, usePlayerName } from "./NameContext";

function Homepage() {
  const navigate = useNavigate();
  const name = usePlayerName();
  const setPlayerName = useSetPlayerName();
  const [showAlert, setShowAlert] = useState(false);

  const handleJoin = () => {
    if (name == "") {
      setShowAlert(true);
    } else {
      navigate("/browse");
    }
  };

  const handleHost = () => {
    if (name == "") {
      setShowAlert(true);
    } else {
      navigate("/play");
    }
  };

  return (
    <>
      <h1>Fight Spare Flee</h1>
      <br />
      <Form.Group className="name-input-group">
        {showAlert && <Alert variant="danger">Enter a name</Alert>}
        <Form.Control
          size="lg"
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setPlayerName(e.target.value)}
        />
      </Form.Group>
      <br />
      <Button variant="primary" className="me-2" size="lg" onClick={handleJoin}>
        Join
      </Button>
      <Button variant="primary" size="lg" onClick={handleHost}>
        Host
      </Button>
    </>
  );
}

export default Homepage;
