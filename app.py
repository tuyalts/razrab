from datetime import datetime
from uuid import UUID
from flask import Flask, request, jsonify

from aggregates import Book, Reader
from clock import SystemClock
from domain import BookId, ReaderId, ISBN, DomainError, DomainInvariantViolation, InvalidValueObject
from lending import LendingId
from process import DebtRegistry, InMemoryLendingRepository, LendingProcess, GatewayUnresolved
from repositories import InMemoryBookRepository, InMemoryReaderRepository
from states import TransitionNotAllowed

app = Flask(__name__)

app.json.ensure_ascii = False

# Инициализация зависимости ОДИН раз при запуске
books_repo = InMemoryBookRepository()
readers_repo = InMemoryReaderRepository()
lendings_repo = InMemoryLendingRepository()
debts = DebtRegistry()
clock = SystemClock()

process = LendingProcess(
    books=books_repo,
    readers=readers_repo,
    lendings=lendings_repo,
    debts=debts,
    clock=clock,
)

# Добавление тестовую книгу и читателя для проверки
book = Book(book_id=BookId.new(), title="1984", isbn=ISBN("9780451524935"), total_copies=5)
reader = Reader(reader_id=ReaderId.new(), name="Селихова П. С.")
books_repo.save(book)
readers_repo.save(reader)

# ОБРАБОТЧИКИ ОШИБОК

@app.errorhandler(TransitionNotAllowed)
def handle_transition_not_allowed(e):
    return jsonify({"error": "TransitionNotAllowed", "message": str(e)}), 409

@app.errorhandler(DomainInvariantViolation)
def handle_invariant_violation(e):
    return jsonify({"error": "InvariantViolation", "message": str(e)}), 422

@app.errorhandler(InvalidValueObject)
def handle_invalid_value(e):
    return jsonify({"error": "InvalidValueObject", "message": str(e)}), 422

@app.errorhandler(DomainError)
def handle_domain_error(e):
    # Если сущность не найдена, DomainError из репозитория выкинет это
    if "не найдена" in str(e):
        return jsonify({"error": "NotFound", "message": str(e)}), 404
    return jsonify({"error": "DomainError", "message": str(e)}), 422

@app.errorhandler(GatewayUnresolved)
def handle_gateway_unresolved(e):
    return jsonify({"error": "GatewayUnresolved", "message": str(e)}), 500

@app.errorhandler(Exception)
def handle_generic_error(e):
    return jsonify({"error": "InternalError", "message": str(e)}), 500


#  МАРШРУТЫ

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/lendings", methods=["POST"])
def create_lending():
    data = request.get_json()
    if not data or "book_id" not in data or "reader_id" not in data:
        return jsonify({"error": "BadRequest", "message": "Нужны book_id и reader_id"}), 400
    try:
        book_id = BookId(UUID(data["book_id"]))
        reader_id = ReaderId(UUID(data["reader_id"]))
    except ValueError:
        return jsonify({"error": "InvalidUUID", "message": "Неверный формат UUID"}), 422
        
    lending = process.reserve_book(book_id, reader_id)
    return jsonify({"lending_id": str(lending.id.value)}), 201

@app.route("/lendings/<lending_id>", methods=["GET"])
def get_lending(lending_id: str):
    lending = lendings_repo.get(LendingId(UUID(lending_id)))
    events = [{"name": e.name, "at": e.occurred_at.isoformat(), "payload": e.payload} for e in lending.events]
    return jsonify({
        "state": lending.state.name,
        "allowed_events": list(lending.allowed_events),
        "events": events
    }), 200

@app.route("/lendings/<lending_id>/reader-arrived", methods=["POST"])
def reader_arrived(lending_id: str):
    process.reader_arrived(LendingId(UUID(lending_id)))
    return jsonify({"status": "ok"}), 200

@app.route("/lendings/<lending_id>/check-debt", methods=["POST"])
def check_debt(lending_id: str):
    process.check_debt(LendingId(UUID(lending_id)))
    return jsonify({"status": "ok"}), 200

@app.route("/lendings/<lending_id>/issue", methods=["POST"])
def issue(lending_id: str):
    process.issue_book(LendingId(UUID(lending_id)))
    return jsonify({"status": "ok"}), 200

@app.route("/lendings/<lending_id>/extend", methods=["POST"])
def extend(lending_id: str):
    process.extend_loan(LendingId(UUID(lending_id)))
    return jsonify({"status": "ok"}), 200

@app.route("/lendings/<lending_id>/return", methods=["POST"])
def return_book(lending_id: str):
    data = request.get_json(silent=True) or {}
    has_damage = data.get("has_damage", False)
    process.return_book(LendingId(UUID(lending_id)), has_damage=has_damage)
    return jsonify({"status": "ok"}), 200

@app.route("/lendings/<lending_id>/pay-debt", methods=["POST"])
def pay_debt(lending_id: str):
    process.pay_debt(LendingId(UUID(lending_id)))
    return jsonify({"status": "ok"}), 200

@app.route("/internal/tick", methods=["POST"])
def tick():
    data = request.get_json() or {}
    now_str = data.get("now")
    if now_str:
        try:
            now = datetime.fromisoformat(now_str)
        except ValueError:
            return jsonify({"error": "InvalidTimeFormat"}), 422
    else:
        now = clock.now()
    
    result = process.tick(now)
    return jsonify(result), 200


if __name__ == "__main__":
    # Выведем ID для удобства тестирования
    print(f"Book ID: {book.id.value}")
    print(f"Reader ID: {reader.id.value}")
    app.run(host="0.0.0.0", port=5000, debug=True)