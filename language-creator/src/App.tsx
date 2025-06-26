import LanguageForm from "./components/LanguageForm/LanguageForm"

function App() {
  return (
    <div className='flex flex-col'>
      <div className="text-center inline-block">
        <p className='text-gray-100 my-3 px-4 py-2 w-fit inline-block border border-blue-600 shadow-blue-600 rounded-lg bg-blue-400 shadow-[inset_0_0_20px_15px,0_4px_5px_1px]'>Curse word bot language creator (by @Poultergeist)</p>
      </div>
      <LanguageForm>

      </LanguageForm>
    </div>
  )
}

export default App
