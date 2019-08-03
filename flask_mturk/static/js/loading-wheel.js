
class LoadingWheel {
    constructor(steps, queue) {
        this.step = 1
        this.steps = steps
        this.last = null
        this.current = queue[0]
        this.next = queue[1]
        this.queue = queue
        this.position = 1
        this.initDOMs()
    }
    initDOMs() {
        this.p_progress = document.getElementById('loading-progress');
        this.p_progress.textContent = this.step + "/" + this.steps;
        this.p_last = document.getElementById('loading-last');
        this.p_last.textContent = this.last;
        this.p_current = document.getElementById('loading-main');
        this.p_current.textContent = this.current;
        this.p_next = document.getElementById('loading-next');
        this.p_next.textContent = this.next;
    }
    nextValue(){
        if (this.queue.length > this.position + 1){
            this.last = this.current;
            this.current = this.next
            this.next = this.queue[this.position + 1]
            this.position++
        }else if(this.queue.length > this.position){
            this.last = this.current;
            this.current = this.next
            this.next = null
            this.position++
        }
        this.update()
    }
    update(){
        this.p_last.textContent = this.last;
        this.p_current.textContent = this.current;
        this.p_next.textContent = this.next;
    }
    push(next) {
        this.last = this.current
        this.current = this.next
        this.next = next
        this.p_last.textContent = this.last;
        this.p_current.textContent = this.current;
        this.p_next.textContent = this.next;
    }
    setCurrent(current){
        this.current = current
        this.p_current.textContent = current;
    }
    setNext(next){
        this.next = next
        this.p_next.textContent = next;
    }
    nextStep(){        
        this.p_progress.textContent = ++this.step + "/" + this.steps;
    }
}