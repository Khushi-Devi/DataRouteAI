const API_URL = "http://127.0.0.1:8000";

const costSlider = document.getElementById("cost");
const latencySlider = document.getElementById("latency");
const reliabilitySlider = document.getElementById("reliability");

const costValue = document.getElementById("costValue");
const latencyValue = document.getElementById("latencyValue");
const reliabilityValue = document.getElementById("reliabilityValue");

let lastTouched = null;


function updatePriorityValues() {
    costValue.textContent = `${costSlider.value}%`;
    latencyValue.textContent = `${latencySlider.value}%`;
    reliabilityValue.textContent = `${reliabilitySlider.value}%`;
}


function adjustSliders(changedSlider) {

    const sliders = [
        costSlider,
        latencySlider,
        reliabilitySlider
    ];

    const otherSliders = sliders.filter(
        slider => slider !== changedSlider
    );

    const changedValue = Number(changedSlider.value);
    const remaining = 100 - changedValue;

    /*
     * If this is the first slider the user touches,
     * distribute the remaining percentage equally.
     */
    if (lastTouched === null) {

        const first = Math.floor(remaining / 2);
        const second = remaining - first;

        otherSliders[0].value = first;
        otherSliders[1].value = second;

    } else {

        /*
         * Keep the previously touched slider fixed.
         * Only the untouched slider absorbs the difference.
         */
        const previouslyTouched = lastTouched;

        const untouchedSlider = otherSliders.find(
            slider => slider !== previouslyTouched
        );

        const previousValue = Number(previouslyTouched.value);

        let newUntouchedValue = 100 - changedValue - previousValue;

        /*
         * Prevent negative values.
         */
        if (newUntouchedValue < 0) {

            newUntouchedValue = 0;

            previouslyTouched.value =
                100 - changedValue;
        }

        untouchedSlider.value = newUntouchedValue;
    }

    lastTouched = changedSlider;

    updatePriorityValues();
}


costSlider.addEventListener("input", () => {
    adjustSliders(costSlider);
});


latencySlider.addEventListener("input", () => {
    adjustSliders(latencySlider);
});


reliabilitySlider.addEventListener("input", () => {
    adjustSliders(reliabilitySlider);
});


updatePriorityValues();


costSlider.addEventListener("input", () => {
    adjustSliders(costSlider);
});

latencySlider.addEventListener("input", () => {
    adjustSliders(latencySlider);
});

reliabilitySlider.addEventListener("input", () => {
    adjustSliders(reliabilitySlider);
});

updatePriorityValues();

costSlider.addEventListener("input", updatePriorityValues);
latencySlider.addEventListener("input", updatePriorityValues);
reliabilitySlider.addEventListener("input", updatePriorityValues);


document.getElementById("optimizeButton").addEventListener(
    "click",
    async () => {

        const source = document.getElementById("source").value;
        const destination = document.getElementById("destination").value;
        const volume = Number(document.getElementById("volume").value);

        const cost = Number(costSlider.value);
        const latency = Number(latencySlider.value);
        const reliability = Number(reliabilitySlider.value);

        const weights = {
            cost: cost / 100,
            latency: latency / 100,
            reliability: reliability / 100
        };

        try {

            const response = await fetch(
                `${API_URL}/optimize-route`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        source_region: source,
                        destination_region: destination,
                        volume_gb: volume,
                        weights: weights
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error("API request failed");
            }

            const best = data.best_route;

            document.getElementById("result")
                .classList.remove("hidden");

            document.getElementById("route").textContent =
                best.route.join(" → ");

            document.getElementById("costResult").textContent =
                `$${best.total_cost}`;

            document.getElementById("latencyResult").textContent =
                `${best.total_latency_ms} ms`;

            document.getElementById("reliabilityResult").textContent =
                `${(best.total_reliability * 100).toFixed(4)}%`;

            document.getElementById("explanation").textContent =
                data.explanation;

        } catch (error) {

            console.error(error);

            alert(
                "Could not connect to DataRoute AI API."
            );
        }
    }
);